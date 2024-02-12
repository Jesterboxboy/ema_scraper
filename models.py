import enum
from sqlalchemy import Enum, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.associationproxy import AssociationProxy
from datetime import datetime
from typing import Optional, List
from sqlalchemy.types import String


class Base(DeclarativeBase):
    pass

metadata = Base.metadata


class RulesetClass(enum.Enum):
    Riichi = "Riichi"
    MCR = "MCR"

Ruleset: Enum = Enum(
    # this may trigger an error in alembic
    # if it does, go into the revision file, and remove the
    # metadata=MetaData() clause where the Column is created
    RulesetClass,
    name="ruleset_type",
    create_constraint=True,
    metadata=Base.metadata,
    validate_strings=True,
)


class Country(Base):
    __tablename__ = "country"
    id: Mapped[str] = mapped_column(String(2), primary_key=True) # iso2
    old3: Mapped[Optional[str]]
    name_english: Mapped[str]
    ema_since: Mapped[Optional[datetime]]
    national_org_name: Mapped[Optional[str]]
    national_org_url: Mapped[Optional[str]]

    players: Mapped[List["Player"]] = relationship(back_populates="country")
    tournaments: Mapped[List["Tournament"]] = relationship(
        back_populates="country")


class PlayerTournament(Base):
    __tablename__ = "player_x_tournament"
    player_id: Mapped[int] = mapped_column(
        ForeignKey("player.id"), primary_key=True)
    tournament_id: Mapped[int] = mapped_column(
        ForeignKey("tournament.id"), primary_key=True
    )
    score: Mapped[int]
    position: Mapped[int]
    base_rank: Mapped[int]
    was_ema: Mapped[bool]

    # we want to record what the country of affiliation was at the time of
    # the event, as this is used to calculate MERS. Affiliation may change
    # after the event, so we need the historic, not live, value
    country_id: Mapped[Optional[str]] = mapped_column(ForeignKey("country.id"))

    player: Mapped["Player"] = relationship(back_populates="tournaments")
    tournament: Mapped["Tournament"] = relationship(back_populates="players")


class Player(Base):
    __tablename__ = "player"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sorting_name: Mapped[str]
    calling_name: Mapped[str]
    ema_id: Mapped[Optional[str]] = mapped_column(String(8))
    country_id: Mapped[Optional[str]] = mapped_column(ForeignKey("country.id"))
    local_club: Mapped[Optional[str]]
    local_club_url: Mapped[Optional[str]]
    profile_pic: Mapped[Optional[str]]

    country: Mapped[Optional[Country]] = relationship(back_populates="players")
    tournaments: Mapped[List[PlayerTournament]] = relationship(
        back_populates="player",
        )
    tournament_weights: AssociationProxy[List[float]] = association_proxy(
        "tournaments",
        "weighting",
        )


class Tournament(Base):
    __tablename__ = "tournament"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    old_id: Mapped[int]
    title: Mapped[str]
    place: Mapped[Optional[str]]
    mers: Mapped[Optional[float]]
    url: Mapped[Optional[str]]
    ruleset: Mapped[str] = mapped_column(Ruleset, nullable=False)
    raw_date: Mapped[Optional[str]]
    start_date: Mapped[datetime]
    end_date: Mapped[datetime]
    effective_end_date: Mapped[datetime]
    player_count: Mapped[int]
    ema_country_count: Mapped[Optional[int]]
    scraped_on: Mapped[Optional[datetime]]

    weighting: Mapped[Optional[int]] # will be calculated live

    country_id: Mapped[Optional[str]] = mapped_column(ForeignKey("country.id"))
    country: Mapped[Optional[Country]] = relationship(back_populates="tournaments")
    players: Mapped[List[PlayerTournament]] = relationship(
        back_populates="tournament")
