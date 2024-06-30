# -*- coding: utf-8 -*-
from datetime import datetime, timezone

from bs4 import BeautifulSoup as bs4
import requests

from models import Player, Ruleset, Settings
from config import HTMLPATH
from utils.ema_jinja import jinja

# TODO these will all go into a css file at some point,
#      but for now, they're easy to edit here
PAGE_STYLES = '''
.ematoggler {cursor:pointer;}
.emahide0 {display: none;}
#mcr_results, #riichi_results {
    border-top: 1px solid #aaf;
    padding-top: 1em;
    margin-top: 1em;
}
.dataTables_filter input[type="search"] {color: #060;}
footer.site-footer {
    color: #666;
    font-size: 0.8em;
    text-align: center;
}
#tablepress-4 {
    margin-top: 1em;
}
#tablepress-4 .column-2, #tablepress-4 .column-8 {
  border-left: 3px double green !important;
}
#tablepress-4 th, #tablepress-4 td {
    text-align: center !important;
}
.emafade {
    color: #666;
}
'''

TOGGLER = """<script>
jQuery(function onready() {
    jQuery('.ematoggler').on('click', function displayhiddenresults(e) {
        jQuery('.emahide0', e.target.parentNode).toggle();
        e.target.remove();
    });
    if (window.location.search.includes('expand=1')) {
            jQuery('.ematoggler').click();
    }
});
</script>"""

class Render_Player:
    '''
    TODO the summary table. By ruleset:
    (pos/N), pts (700.12), #MERS tourns, #1sts, #2nds, #3rds, #non-MERS tourns
    '''
    def __init__(self, db):
        self.db = db
        r = requests.get("https://silk.mahjong.ie/template-player")
        self.template = r.content
        self.totals = {
            'mcr': self.db.query(Settings.value).filter_by(
                key='player_count_mcr').first()[0],
            'riichi': self.db.query(Settings.value).filter_by(
                key='player_count_riichi').first()[0]
            }

    def fill_player_summary_table(self, dom):
        '''
        key = f"player_count_{rules}"
        setting = self.db.query(Settings).filter_by(key=key).first()
        '''
        zone = dom.find(id="tablepress-4").find("tbody")
        j = jinja.from_string(str(zone))
        new_row = j.render(c=self.counts, p=self.p, t=self.totals)
        zone.replace_with(bs4(new_row, 'html.parser'))

    def fill_player_tournament_table(self, dom, rules, results):
        zone = dom.find(id=f"{rules}_results")
        if not(len(results)):
            zone.decompose()
            return
        tbody = zone.find("tbody")
        row = tbody.find("tr")
        row['class'].append(
            '{% if not t.tournament.age_factor %}emahide0{% endif %}')

        results.sort(
                key=lambda t: t.tournament.end_date,
                reverse=True,
                )

        ranked_count = 0
        nonranked_count = 0
        count_1st = 0
        count_2nd = 0
        count_3rd = 0

        results_to_hide = 0
        for r in results:
            j = jinja.from_string(str(row))
            new_row = j.render(t=r)
            tbody.append(bs4(new_row, 'html.parser'))
            if r.tournament.age_factor == 0:
                results_to_hide += 1
                nonranked_count += 1
            else:
                ranked_count += 1
                match r.position:
                    case 1:
                        count_1st += 1
                    case 2:
                        count_2nd += 1
                    case 3:
                        count_3rd += 1

        if results_to_hide:
            # add a toggle to show tournaments with age 0
            toggler = bs4(
                f'''<a class=ematoggler>Show the {results_to_hide} results that
                no longer contribute to rank</a>''',
                "html.parser"
                )
            zone.append(toggler)

        self.counts[rules] = (ranked_count , count_1st, count_2nd,
                                 count_3rd, nonranked_count)

        # remove the template row, we've finished with it now
        row.decompose()

    def one_player(self, id):
        print('.', end='')
        self.counts = {'mcr': [0,0,0,0,0], 'riichi': [0,0,0,0,0]}
        self.p = self.db.query(Player).filter(Player.ema_id == id).first()
        dom = bs4(self.template, "html.parser")
        dom.select_one("style").append(PAGE_STYLES)
        # allocate tournaments to rulesets, most recent first
        riichi = []
        mcr = []
        for r in self.p.tournaments:
            if r.ruleset == Ruleset.riichi:
                riichi.append(r)
            else:
                mcr.append(r)

        player_zone = dom.find(id="player_data")

        t = jinja.from_string(str(player_zone))
        new_text = t.render(p=self.p)
        player_zone.replace_with(bs4(new_text, "html.parser"))

        self.fill_player_tournament_table(dom, 'mcr', mcr)
        self.fill_player_tournament_table(dom, 'riichi', riichi)

        self.fill_player_summary_table(dom)

        dom.find(id='colophon').replace_with(bs4(
            f'''<footer class="site-footer" role="contentinfo">Updated:
            {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S %z')}
            </footer>''',
            features="html.parser"))
        dom.body.append(bs4(TOGGLER, "html.parser"))
        with open(HTMLPATH / "Players" / f"{self.p.id}.html",
                  "w", encoding='utf-8') as file:
            file.write(str(dom))

        # add a redirect from the old player profile url
        with open(HTMLPATH / "Players" / f"{self.p.ema_id}.html", "w",
                  encoding='utf-8') as file:
            file.write(f'''<?php
                       header("HTTP/1.1 301 Moved Permanently");
                       header("Location: /ranking/Players/{self.p.id}");
                       exit();''')

        # add a redirect from the old player history url
        with open(HTMLPATH / "Players" / f"{self.p.ema_id}_History.html", "w",
                  encoding='utf-8') as file:
            file.write(f'''<?php
                header("HTTP/1.1 301 Moved Permanently");
                header("Location: /ranking/Players/{self.p.id}?expand=1");
                exit();''')
