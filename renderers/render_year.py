# -*- coding: utf-8 -*-
"""
"""
from datetime import datetime, timezone

from bs4 import BeautifulSoup as bs4
import requests
from sqlalchemy import extract

from config import HTMLPATH
from utils.ema_jinja import jinja
from models import RulesetClass, Tournament

PAGE_STYLES = '''
.tablepress-id-5 td {
  vertical-align: middle !important;
}
.tablepress-id-5 td.column-3,
.tablepress-id-5 td.column-4,
.tablepress-id-5 td.column-5,
.tablepress-id-5 td.column-6,
.tablepress-id-5 td.column-7 {
  text-align: center !important;
}
.dataTables_filter input[type="search"] {color: #060;}
'''

TOGGLER = """<script>
jQuery(function onready() {
  jQuery('.ematoggler').on('click', function displayhiddenresults(e) {
    jQuery('.dataTables_wrapper',
           jQuery(e.target).parents('div').eq(0)).toggle();
  });
});
</script>"""

class Render_Year:

    def __init__(self, db):
        self.db = db
        r = requests.get("https://silk.mahjong.ie/template-year")
        self.template = r.content

    def render(self, year: int) -> None:
        dom = bs4(self.template, "html.parser")
        dom.select_one("style").append(PAGE_STYLES)
        print('.', end='')

        h1 = dom.find('h1', {'class': 'entry-title'})
        j = jinja.from_string(str(h1))
        h1.replace_with(bs4(j.render(year=year), 'html.parser'))
        j = jinja.from_string(dom.title.string)
        dom.title.string.replace_with(bs4(j.render(year=year), 'html.parser'))

        for rules in RulesetClass:
            rulestring = 'mcr' if rules == RulesetClass.mcr else 'riichi'
            zone = dom.find(id=f"{rulestring}").find('table')
            tbody = zone.find("tbody")
            row = tbody.find("tr")

            tournaments = self.db.query(Tournament).filter(
                extract("year", Tournament.start_date) ==  year).filter(
                    Tournament.ruleset == rules).all()

            if not len(tournaments):
                zone.decompose()
                continue

            for t in tournaments:
                j = jinja.from_string(str(row))
                new_row = j.render(t=t)
                tbody.append(bs4(new_row, 'html.parser'))

            # remove the template row, we've finished with it now
            row.decompose()

        dom.find(id='colophon').replace_with(bs4(
            f'''<footer class="site-footer" role="contentinfo">Page last cached:
            {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S %z')}
            </footer>''',
            features="html.parser"))

        dom.body.append(bs4(TOGGLER, "html.parser"))

        with open(HTMLPATH / "Tournaments" / f"Tournaments_{year}.html",
                  "w",
                  encoding='utf-8') as file:
            file.write(str(dom))

    def years(self, start=2005, end=datetime.now().year):
        for y in range(start, end+1):
            self.render(y)
