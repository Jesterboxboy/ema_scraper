from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
# from sqlalchemy.ext.associationproxy import association_proxy
# from sqlalchemy.ext.associationproxy import AssociationProxy
from datetime import datetime
from typing import Optional, Set
from sqlalchemy.types import String

class Base(DeclarativeBase):
    pass

metadata = Base.metadata


class Country(Base):
    __tablename__ = "country"
    id: Mapped[str] = mapped_column(String(2), primary_key=True)
    name_english: Mapped[str]
    name_native: Mapped[str]
    ema_since: Mapped[datetime]
    players: Mapped[Set["Player"]] = relationship(back_populates="country")
    tournaments: Mapped[Set["Tournament"]] = relationship(back_populates="country")


class PlayerTournament(Base):
    __tablename__ = "player_x_tournament"
    player_id: Mapped[int] = mapped_column(ForeignKey("player.id"), primary_key=True)
    tournament_id: Mapped[int] = mapped_column(
        ForeignKey("tournament.id"), primary_key=True
    )
    actual_rank: Mapped[int]
    base_rank: Mapped[int]
    player: Mapped["Player"] = relationship(back_populates="tournaments")
    tournament: Mapped["Tournament"] = relationship(back_populates="players")

    # we want to record what the  country of affiliation was at the time of
    # the event. (It may change afterwards)
    country_id: Mapped[str] = mapped_column(ForeignKey("country.id"))


class Player(Base):
    __tablename__ = "player"
    id: Mapped[int] = mapped_column(primary_key=True)
    sorting_name: Mapped[str]
    calling_name: Mapped[str]
    old_ema_id: Mapped[str] = mapped_column(String(8))
    country_id: Mapped[str] = mapped_column(ForeignKey("country.id"))
    local_club: Mapped[Optional[str]]
    local_club_url: Mapped[Optional[str]]
    tournaments: Mapped[Set[PlayerTournament]] = relationship(back_populates="player")
    country: Mapped["Country"] = relationship(back_populates="players")


class Tournament(Base):
    __tablename__ = "tournament"
    id: Mapped[int] = mapped_column(primary_key=True)
    mers: Mapped[float]
    name: Mapped[str]
    url: Mapped[str]
    ruleset: Mapped[str] # TODO enum or something: Riichi || MCR
    start_date: Mapped[datetime]
    end_date: Mapped[datetime]
    effective_end_date: Mapped[datetime]
    country_id: Mapped[str] = mapped_column(ForeignKey("country.id"))
    country: Mapped["Country"] = relationship(back_populates="tournaments")
    players: Mapped[Set[PlayerTournament]] = relationship(back_populates="tournament")
    nPlayers: Mapped[int]
    nEMACountries: Mapped[int]
