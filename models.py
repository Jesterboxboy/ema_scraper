from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, List

from sqlalchemy import Enum, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import String


class Base(DeclarativeBase):
    pass

metadata = Base.metadata


class Ruleset(PyEnum):
    riichi = "riichi"
    mcr = "mcr"


class Settings(Base):
    ''' this is a miscellaneous collection of values that don't fit
    anywhere else'''
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str]


class Social(Base):
    ''' each row is one social network link, for one club
    A club may have multiple social links,
    but each social link belongs to exactly one club'''
    __tablename__ = "social"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    url: Mapped[str]
    network_name: Mapped[str]
    club_id: Mapped[int] = mapped_column(ForeignKey("club.id"))
    club: Mapped["Club"] = relationship(back_populates="socials")


class Club(Base):
    ''' can be a local club or a national org '''
    __tablename__ = "club"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str]
    url: Mapped[Optional[str]]
    logo_url: Mapped[Optional[str]]
    is_the_national_org: Mapped[bool]
    country_id: Mapped[Optional[str]] = mapped_column(ForeignKey("country.id"))
    players: Mapped[List["Player"]] = relationship(back_populates="local_club")
    socials: Mapped[List[Social]] = relationship(back_populates="club")


class Country(Base):
    __tablename__ = "country"
    id: Mapped[str] = mapped_column(String(2), primary_key=True) # iso2
    old3: Mapped[Optional[str]]
    name_english: Mapped[str]
    ema_since: Mapped[Optional[datetime]]
    #national_org_id: Mapped[Optional[int]] = mapped_column(ForeignKey("club.id"))
    #national_org: Mapped[Club] = relationship(back_populates="players")

    country_ranking_mcr: Mapped[Optional[int]]
    # number of qualifying players
    player_count_mcr: Mapped[Optional[int]]
    # number of players with personal rank over 700
    over700_mcr: Mapped[Optional[int]]
    average_rank_of_top3_players_mcr: Mapped[Optional[float]]
    # number of ranked players / total EMA-wide number of ranked players
    propn_of_all_ranked_players_mcr: Mapped[Optional[float]]
    # number of 700+ players / total EMA-wide number of 700+ players
    propn_of_all_players_700plus_mcr: Mapped[Optional[float]]

    country_ranking_riichi: Mapped[Optional[int]]
    # number of qualifying players
    player_count_riichi: Mapped[Optional[int]]
    # number of players with personal rank over 700
    over700_riichi: Mapped[Optional[int]]
    average_rank_of_top3_players_riichi: Mapped[Optional[float]]
    # number of ranked players / total EMA-wide number of ranked players
    propn_of_all_ranked_players_riichi: Mapped[Optional[float]]
    # number of 700+ players / total EMA-wide number of 700+ players
    propn_of_all_players_700plus_riichi: Mapped[Optional[float]]

    players: Mapped[List["Player"]] = relationship(back_populates="country")
    tournaments: Mapped[List["Tournament"]] = relationship(
        back_populates="country")


class PlayerTournament(Base):
    ''' many-to-many mapping of players & tournaments '''
    __tablename__ = "player_x_tournament"
    player_id: Mapped[int] = mapped_column(
        ForeignKey("player.id"), primary_key=True)
    tournament_id: Mapped[int] = mapped_column(
        ForeignKey("tournament.id"), primary_key=True
    )
    score: Mapped[int]
    table_points: Mapped[Optional[float]]
    position: Mapped[int]
    base_rank: Mapped[int]
    was_ema: Mapped[bool]
    aged_rank: Mapped[Optional[float]]
    aged_mers: Mapped[Optional[float]]
    # duplicating ruleset here means we don't need a join, but it's bad coding
    ruleset: Mapped[Ruleset] = mapped_column(Enum(Ruleset), nullable=False)
    # we want to record what the country of affiliation was at the time of
    # the event, as this is used to calculate MERS. Affiliation may change
    # after the event, so we need the historic, not live, value
    country_id: Mapped[Optional[str]] = mapped_column(ForeignKey("country.id"))

    player: Mapped["Player"] = relationship(
        back_populates="tournaments",
        #order_by="PlayerTournament.tournament.end_date.desc()",
        )
    tournament: Mapped["Tournament"] = relationship(back_populates="players")


class Player(Base):
    __tablename__ = "player"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sorting_name: Mapped[str]
    calling_name: Mapped[str]
    ema_id: Mapped[Optional[str]] = mapped_column(String(8))
    country_id: Mapped[Optional[str]] = mapped_column(ForeignKey("country.id"))
    local_club_id: Mapped[Optional[int]] = mapped_column(ForeignKey("club.id"))
    local_club: Mapped[Club] = relationship(back_populates="players")
    profile_pic: Mapped[Optional[str]]

    mcr_rank: Mapped[Optional[float]]
    mcr_official_rank: Mapped[Optional[float]]
    mcr_position: Mapped[Optional[int]]

    riichi_rank: Mapped[Optional[float]]
    riichi_official_rank: Mapped[Optional[float]]
    riichi_position: Mapped[Optional[int]]

    country: Mapped[Optional[Country]] = relationship(back_populates="players")
    tournaments: Mapped[List[PlayerTournament]] = relationship(
        back_populates="player",
        )

    def rank(self, ruleset, rank: int):
        if rank is not None:
            rank = round(rank * 100) / 100
        if ruleset == Ruleset.mcr:
            self.mcr_rank = rank
        else:
            self.riichi_rank = rank


class Tournament(Base):
    __tablename__ = "tournament"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    old_id: Mapped[int]
    title: Mapped[str]
    place: Mapped[Optional[str]]
    mers: Mapped[Optional[float]]
    url: Mapped[Optional[str]]
    ruleset: Mapped[Ruleset] = mapped_column(Enum(Ruleset), nullable=False)
    raw_date: Mapped[Optional[str]]
    start_date: Mapped[datetime]
    end_date: Mapped[datetime]
    effective_end_date: Mapped[datetime]
    player_count: Mapped[int]
    ema_country_count: Mapped[Optional[int]]
    scraped_on: Mapped[Optional[datetime]]
    age_factor: Mapped[Optional[float]]

    country_id: Mapped[Optional[str]] = mapped_column(ForeignKey("country.id"))
    country: Mapped[Optional[Country]] = relationship(back_populates="tournaments")
    players: Mapped[List[PlayerTournament]] = relationship(
        back_populates="tournament")
