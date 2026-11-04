"""Links page and the home page."""
from wiki import core
from wiki.core import INDEX, PAGES, Raw, card, esc, page, page_icon, t, table


LINK_SECTIONS = [  # (anchor, section_title, [(title, url, what_it_is), ...])
    ("tools", "Калькуляторы и инструменты", [
        ("BTD6 Open Data", "https://btd6data.com", "Инструменты и лидерборды по API: боссы, гонки, тайминги ферм, профили по OAK."),
        ("BTD6 Portal", "https://btd6portal.com", "Калькуляторы степени парагона, калькулятор фарма и испытания сообщества."),
        ("BTD6 Paragon Calculator", "https://kaister300.github.io/BTD6ParagonCalculator/", "Калькулятор степени парагона."),
        ("BTD6 Hero XP Calculator", "https://svrng.github.io/BTD6-Hero-XP-Calculator/", "Калькулятор опыта героев."),
    ]),
    ("wikis", "Вики и базы знаний", [
        ("Blooncyclopedia", "https://www.bloonswiki.com", "Большая вики по всем играм Bloons: тексты, история изменений, стратегии."),
        ("Bloons Wiki (Fandom)", "https://bloons.fandom.com/wiki/Bloons_Wiki", "Старейшая вики сообщества: подробные статьи по механикам, башням, обновлениям и лору."),
        ("The BTD6 Index", "https://btd6index.win", "База соревновательных рекордов сообщества: 2TC (2 башни CHIMPS), 2MPC (2 млн урона одной башней), Least Cash."),
        ("BTD6 Maplist", "https://btd6maplist.sarto.dev/", "Рейтинг сложнейших пользовательских карт, пройденных на CHIMPS, по аналогии с Demon List."),
    ]),
    ("mods", "Моддинг и разработка", [
        ("BTD6 Mod Helper", "https://github.com/gurrenm3/BTD-Mod-Helper", "Библиотека для модов, через неё выгружены данные этого сайта."),
        ("BTD6 Mod Manager", "https://github.com/TDToolbox/BTD6-Mod-Manager", "Удобный менеджер модов для BTD6: установка и управление модами и MelonLoader в один клик."),
        ("BTD6 API Explorer", "https://btd6apiexplorer.github.io/", "Веб-интерфейс для просмотра данных официального Ninja Kiwi Open Data API."),
        ("BTD6 Tech Wiki", "https://github.com/Antonzlo/btd6-tech-wiki", "Исходный код этого сайта."),
    ]),
    ("community", "Сообщество и разработчики", [
        ("Ninja Kiwi", "https://ninjakiwi.com", "Разработчики игры: новости и патчноуты."),
        ("Ninja Kiwi Discord", "https://discord.gg/ninjakiwi", "Официальный Discord-сервер разработчиков: анонсы, общение и поиск напарников для Co-op."),
        ("r/btd6", "https://www.reddit.com/r/btd6/", "Сообщество игры на Reddit."),
        ("Cyber Quincy", "https://github.com/hemisemidemipresent/cyberquincy", "Discord-бот сообщества для поиска точных характеристик башен (Popology), кривых опыта героев и дохода."),
    ]),
]


def build_links():
    cards = []
    toc = []
    for anchor, title, links in LINK_SECTIONS:
        rows = []
        for n, u, d in links:
            rows.append((Raw(f"<a href='{u}' rel='noopener'><b>{esc(n)}</b></a>"), d))
            INDEX.append([n, title, f"{core.current_file}#{anchor}", d])
        cards.append(card(anchor, title, table(["Сайт", "Что там"], rows), section="Ссылки"))
        toc.append((anchor, title))
    page("links.html", "Ссылки", "", "".join(cards), toc=toc)


def build_index():
    tiles = "".join(f"<a class='tile page-tile' href='{f}'>{page_icon(f, 56)}<span><b>{esc(t(n, fallback=n))}</b><small>{esc(s)}</small></span></a>" for f, n, s in PAGES[1:])
    page("index.html", "BTD6 Tech Wiki",
         "Точные числа Bloons TD 6 из файлов игры: урон и цены башен, уровни героев, HP боссов, "
         "режимы, доход, баффы. Поиск по сайту: клавиша /.",
         f"<div class='grid home-grid'>{tiles}</div>")
