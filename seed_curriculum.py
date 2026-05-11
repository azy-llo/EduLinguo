"""
Генерация уровней A1–C1: по 50 уроков (Grammar, Vocabulary, Reading, Writing, Listening по 10)
+ итоговый экзамен. Вызывается один раз при пустой таблице levels.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import func, select

from models import Exercise, Lesson, Level, db

ASPECTS = ("grammar", "vocabulary", "reading", "writing", "listening")
LESSONS_PER_LEVEL = 50
EXAM_ORDER = 51

GRAMMAR_TOPICS = {
    "A1": [
        "Present simple of <em>to be</em>: <strong>I am / You are / He is</strong>.",
        "Articles <strong>a / an</strong> with singular nouns.",
        "Plural nouns: add <strong>-s</strong> or <strong>-es</strong>.",
        "Possessive adjectives: <strong>my, your, his, her</strong>.",
        "Questions with <strong>What / Where / Who</strong>.",
        "Present simple: <strong>I work / She works</strong>.",
        "Negatives: <strong>don't / doesn't</strong>.",
        "Imperatives: <strong>Open / Don't open</strong>.",
        "There is / There are.",
        "Countable vs uncountable (basics).",
    ],
    "A2": [
        "Past simple: regular and common irregular verbs.",
        "Was / were in the past.",
        "Going to for future plans.",
        "Present continuous for now.",
        "Comparatives: <strong>older than / more interesting</strong>.",
        "Superlatives: <strong>the best / the most</strong>.",
        "Countable nouns with <strong>some / any</strong>.",
        "Modals: <strong>can / could / must</strong> (introduction).",
        "First conditional (basic).",
        "Present perfect with <strong>ever / never</strong> (intro).",
    ],
    "B1": [
        "Present perfect vs past simple.",
        "Past continuous and past simple together.",
        "Second conditional.",
        "Reported speech (statements).",
        "Passive voice (present and past).",
        "Relative clauses: <strong>who / which / that</strong>.",
        "Gerunds and infinitives (patterns).",
        "Present perfect continuous.",
        "Modals of deduction: <strong>might / must / can't</strong>.",
        "Question tags (basic rules).",
    ],
    "B2": [
        "Mixed conditionals.",
        "Past perfect and narrative cohesion.",
        "Passive with reporting verbs.",
        "Subjunctive / unreal past (<strong>wish / if only</strong>).",
        "Cleft sentences (<strong>It was John who…</strong>).",
        "Inversion (<strong>Never have I…</strong>) — introduction.",
        "Participle clauses.",
        "Future perfect / future continuous.",
        "Modals in the past (<strong>should have</strong>).",
        "Ellipsis and substitution.",
    ],
    "C1": [
        "Nuanced modality and hedging.",
        "Advanced passive and impersonal structures.",
        "Subtle conditionals and alternatives to <strong>if</strong>.",
        "Discourse markers in formal writing.",
        "Complex noun phrases.",
        "Emphasis and focus structures.",
        "Advanced reported speech.",
        "Colloquial vs formal grammar choices.",
        "Concessive clauses (<strong>while / whereas / albeit</strong>).",
        "Conciseness and redundancy editing.",
    ],
}


def _ex(lesson_id: int, order_index: int, kind: str, prompt: str, payload: dict[str, Any]) -> Exercise:
    return Exercise(
        lesson_id=lesson_id,
        order_index=order_index,
        kind=kind,
        prompt=prompt,
        payload_json=json.dumps(payload, ensure_ascii=False),
    )


def _aspect_for_order(order: int) -> str:
    if order < 1 or order > LESSONS_PER_LEVEL:
        return "exam"
    return ASPECTS[(order - 1) % 5]


def _sub_index(order: int) -> int:
    return (order - 1) // 5 + 1


def _grammar_topic(level: str, sub: int) -> str:
    topics = GRAMMAR_TOPICS.get(level, GRAMMAR_TOPICS["A1"])
    return topics[(sub - 1) % len(topics)]


def _grammar_theory(level: str, sub: int) -> str:
    topic = _grammar_topic(level, sub)
    # Извлекаем ключевое слово темы (например, "Present simple", "Articles", "Past simple")
    topic_lower = topic.lower()

    # Базовые универсальные советы (короткие)
    base_tips = [
        "Прочитайте правило ниже и обратите внимание на форму глагола.",
        "Попробуйте составить 2-3 своих примера по этому правилу.",
        "Затем выполните тестовые задания, чтобы закрепить."
    ]

    # Специфические советы в зависимости от темы
    specific_tips = []

    if "present simple" in topic_lower:
        specific_tips = [
            "Для he/she/it добавляйте окончание -s к глаголу (works, plays, goes).",
            "В отрицаниях используйте don't / doesn't + глагол без -s.",
            "В вопросах начинайте с Do / Does.",
            "Маркеры: always, usually, often, sometimes, never, every day."
        ]
    elif "to be" in topic_lower:
        specific_tips = [
            "Запомните формы: I am, you are, he/she/it is, we/they are.",
            "Отрицание: am not, is not (isn't), are not (aren't).",
            "Вопрос: Am I? Is he? Are they?",
            "To be НЕ требует вспомогательного do/does в вопросах и отрицаниях."
        ]
    elif "article" in topic_lower or "a / an" in topic_lower or "the" in topic_lower:
        specific_tips = [
            "A/an — для исчисляемых существительных в единственном числе впервые.",
            "An ставится перед гласным звуком: an apple, an hour.",
            "The — когда предмет уже известен или единственный в мире.",
            "Нулевой артикль с неисчисляемыми и множественными в общем смысле."
        ]
    elif "past simple" in topic_lower:
        specific_tips = [
            "Правильные глаголы: V2 = V + ed (worked, played).",
            "Неправильные глаголы нужно запоминать (go-went, have-had).",
            "Отрицание: didn't + V1 (без -ed).",
            "Вопрос: Did + подлежащее + V1?",
            "Маркеры: yesterday, last week, in 2010, ago."
        ]
    elif "present perfect" in topic_lower:
        specific_tips = [
            "Формула: have/has + V3 (причастие прошедшего времени).",
            "Употребляется для результата, опыта, действия до текущего момента.",
            "Маркеры: ever, never, already, yet, just, since, for.",
            "Если указано точное время в прошлом (yesterday, last year), используйте Past Simple."
        ]
    elif "comparative" in topic_lower or "superlative" in topic_lower:
        specific_tips = [
            "Для коротких прилагательных: -er / -est (taller, the tallest).",
            "Для длинных: more / most (more interesting, the most interesting).",
            "Исключения: good → better → best, bad → worse → worst.",
            "Сравнения: than (He is taller than me)."
        ]
    elif "conditional" in topic_lower:
        specific_tips = [
            "1st conditional: If + Present, will + V1 (реальный будущий результат).",
            "2nd conditional: If + Past Simple, would + V1 (воображаемая ситуация).",
            "3rd conditional: If + Past Perfect, would have + V3 (сожаление о прошлом)."
        ]
    elif "passive" in topic_lower:
        specific_tips = [
            "Формула: to be + V3 (ed для правильных).",
            "Время показывает to be (is made, was built, will be done).",
            "Агент (by someone) часто опускается, если не важен."
        ]
    else:
        # Если тема не распознана, даём общие советы
        specific_tips = [
            "Обратите внимание на форму глагола и порядок слов.",
            "Проверьте согласование подлежащего и сказуемого.",
            "Используйте маркеры времени, если они есть."
        ]

    all_tips = specific_tips + base_tips
    tips_html = "".join(f"<li>{tip}</li>" for tip in all_tips)

    return (
        f"<p><strong>Грамматика · {level} · урок {sub}</strong></p>"
        f"<p><strong>Тема урока:</strong> {topic}</p>"
        "<p><strong>Советы по теме:</strong></p>"
        f"<ol>{tips_html}</ol>"
    )


def _reading_passage(level: str, sub: int) -> str:
    bodies = {
        "A1": [
            "My name is Tom. I am from London. I am a student. I like coffee and books.",
            "Anna works in a small shop. The shop is open every day. Customers buy fruit and bread.",
            "It is Sunday. The family is at home. They cook lunch and watch a funny film.",
            "Peter has a dog. The dog likes long walks in the park. Peter is happy after the walk.",
            "Our classroom is big. There are twelve chairs. The teacher writes on the board.",
        ],
        "A2": [
            "Last weekend we visited a museum in the city centre. The tickets were cheap and the guide explained everything clearly.",
            "Maria is learning English because she wants a better job. She studies for one hour after work every evening.",
            "The weather was bad yesterday, so we stayed inside. Today the sun is shining and we will go cycling.",
            "If you want healthy food, try this café. They use fresh vegetables and they do not add much sugar.",
            "The train was late, but we still arrived before the meeting. Next time we will leave earlier.",
        ],
        "B1": [
            "Although the project faced several delays, the team delivered a working prototype before the deadline. Stakeholders appreciated the transparent communication.",
            "Many young people choose online courses because they can study at their own pace. However, self-discipline remains essential.",
            "The article discusses how social media affects attention spans. Critics argue that constant notifications fragment concentration.",
            "Renewable energy is becoming cheaper, yet infrastructure investment is still uneven across regions.",
            "Working from home offers flexibility, but it can blur boundaries between personal life and work.",
        ],
        "B2": [
            "Had the negotiations failed, the company would have faced substantial losses; fortunately, a compromise was reached at the last minute.",
            "Not only does regular exercise improve physical health, but it also appears to benefit cognitive performance in the long term.",
            "The novel subtly critiques consumer culture without resorting to overt moralising, which many readers find refreshing.",
            "Little did we realise at the time how profoundly the policy would reshape the industry within a decade.",
            "Such was the demand for tickets that the website crashed within minutes of the sale opening.",
        ],
        "C1": [
            "The essay contends that ostensibly neutral algorithms may encode biases inherited from training data, thereby perpetuating systemic inequities under the guise of objectivity.",
            "Were policymakers to internalise the full externalities of carbon-intensive industries, fiscal instruments would arguably need recalibration.",
            "Seldom has public discourse been so polarised, yet there remain pockets of cross-partisan collaboration worth amplifying.",
            "So intricate is the interplay between migration, labour markets, and housing policy that single-factor explanations invariably fall short.",
            "Not until the longitudinal study had been replicated did the medical community treat the findings as conclusive.",
        ],
    }
    arr = bodies.get(level, bodies["A1"])
    text = arr[(sub - 1) % len(arr)]
    return f'<div class="reading-passage-inner"><p class="reading-label">Текст для чтения</p><p>{text}</p></div>'


def _listening_word(level: str, sub: int, n: int) -> str:
    """n — номер под-упражнения 0..3."""
    banks = {
        "A1": ["hello", "water", "school", "family", "morning", "friend", "happy", "table", "music", "window", "flower", "girl", "man", "boy"],
        "A2": ["discount", "receipt", "journey", "weather", "borrow", "advice", "enough", "foreign", "quiet", "bridge"],
        "B1": ["although", "achieve", "environment", "government", "opportunity", "convenient", "suggest", "develop", "reduce", "increase"],
        "B2": ["nevertheless", "assumption", "significant", "undermine", "scrutiny", "prevalent", "coherent", "implication", "subsequent", "comprehensive"],
        "C1": ["ubiquitous", "paradigm", "nuance", "meticulous", "ambiguous", "pragmatic", "dichotomy", "salient", "tenuous", "ephemeral"],
    }
    b = banks.get(level, banks["A1"])
    idx = ((sub - 1) * 4 + n) % len(b)
    return b[idx]


def _writing_topic(level: str, sub: int) -> tuple[str, int, list[str]]:
    topics = {
        "A1": [
            ("Опишите свой день в 3–5 предложениях на английском (утро, работа/учёба, вечер).", 20, ["i", "day", "work"]),
            ("Напишите о своей семье: кто есть в семье и где вы живёте.", 20, ["family", "live", "my"]),
        ],
        "A2": [
            ("Расскажите о последних выходных: что вы делали и с кем.", 35, ["weekend", "because", "went"]),
            ("Опишите любимое место в городе и почему оно вам нравится.", 35, ["place", "like", "because"]),
        ],
        "B1": [
            ("Тема: плюсы и минусы соцсетей. Напишите 80–120 слов.", 60, ["however", "people", "think"]),
            ("Тема: как вы учите английский и что вам помогает.", 60, ["learn", "english", "help"]),
        ],
        "B2": [
            ("Согласны ли вы, что удалённая работа изменила баланс жизни? Аргументируйте.", 90, ["although", "work", "life"]),
            ("Короткое эссе: важность чтения книг в эпоху коротких видео.", 90, ["reading", "attention", "deep"]),
        ],
        "C1": [
            (
                "Письменное рассуждение: насколько оправданы жёсткие меры в ответ на глобальные кризисы? Уровень C1.",
                120,
                ["policy", "trade", "off", "society"],
            ),
            (
                "Проанализируйте роль критического мышления в потреблении новостей.",
                120,
                ["evidence", "bias", "source", "evaluate"],
            ),
        ],
    }
    arr = topics.get(level, topics["A1"])
    t, mw, kw = arr[(sub - 1) % len(arr)]
    return t, mw, kw


def build_grammar_exercises(lesson_id: int, level: str, sub: int) -> list[Exercise]:
    topic = _grammar_topic(level, sub)
    packs = [
        {
            "q1": ("Выберите правильную форму to be для I", ["am", "is", "are", "be"], 0),
            "q2": (
                "Выберите грамматически верное предложение:",
                ["She goes to school every day.", "She go to school every day.", "She going to school every day.", "She are at school."],
                0,
            ),
            "q3_tokens": ["They", "don't", "like", "cold", "weather", "."],
            "q4": ("Выберите правильное отрицание:", ["He doesn't work here.", "He don't work here.", "He not work here.", "He doesn't works here."], 0),
        },
        {
            "q1": ("Выберите правильный артикль: ___ apple", ["a", "an", "the", "—"], 1),
            "q2": (
                "Выберите правильный вариант:",
                ["I have an umbrella.", "I have a umbrella.", "I has an umbrella.", "I have umbrella the."],
                0,
            ),
            "q3_tokens": ["This", "is", "an", "interesting", "book", "."],
            "q4": ("Где нужен the?", ["Close the door, please.", "Close door, please.", "Close a door, please.", "Close an door, please."], 0),
        },
        {
            "q1": ("Выберите множественное число слова child", ["childs", "children", "childes", "childrens"], 1),
            "q2": (
                "Выберите правильное предложение:",
                ["These boxes are heavy.", "These box are heavy.", "This boxes are heavy.", "These boxes is heavy."],
                0,
            ),
            "q3_tokens": ["Two", "cars", "are", "outside", "."],
            "q4": ("Выберите корректную форму:", ["Many people are here.", "Many peoples are here.", "Many person are here.", "Many people is here."], 0),
        },
        {
            "q1": ("Выберите верное притяжательное местоимение: ___ book (for she)", ["his", "her", "their", "its"], 1),
            "q2": ("Выберите верную фразу:", ["This is my phone.", "This is me phone.", "This is I phone.", "This is mine phone."], 0),
            "q3_tokens": ["Our", "teacher", "is", "very", "kind", "."],
            "q4": ("Выберите правильный вариант:", ["Their house is big.", "There house is big.", "Them house is big.", "They house is big."], 0),
        },
        {
            "q1": ("Выберите правильное вопросительное слово: ___ is your name?", ["What", "Where", "Who", "When"], 0),
            "q2": ("Выберите корректный вопрос:", ["Where do you live?", "Where you live?", "Where does you live?", "Where do lives you?"], 0),
            "q3_tokens": ["What", "is", "your", "job", "?" ],
            "q4": ("Выберите правильный вариант:", ["Who is your teacher?", "Who your teacher is?", "Who are your teacher?", "Who do your teacher?"], 0),
        },
    ]
    pack = packs[(sub - 1) % len(packs)]
    q1, o1, c1 = pack["q1"]
    q2, o2, c2 = pack["q2"]
    q4, o4, c4 = pack["q4"]
    return [
        _ex(lesson_id, 1, "translate", f"{q1} ", {"options": o1, "correct_index": c1}),
        _ex(lesson_id, 2, "phrases", f"{q2}", {"options": o2, "correct_index": c2}),
        _ex(lesson_id, 3, "reorder", f"Соберите предложение ", {"tokens": pack["q3_tokens"]}),
        _ex(lesson_id, 4, "translate", f"{q4} ", {"options": o4, "correct_index": c4}),
        _ex(lesson_id, 5, "words", "Слово «grammar» значит…", {"options": ["грамматика", "география", "арифметика", "музыка"], "correct_index": 0}),
    ]


def build_vocab_exercises(lesson_id: int, level: str, sub: int) -> list[Exercise]:
    base = (sub - 1) * 3
    w1 = ["house", "garden", "kitchen", "street"][base % 4]
    return [
        _ex(lesson_id, 1, "words", f"Подберите значение слова «{w1}» (уровень {level}).", {"options": ["дом", "лес", "река", "небо"], "correct_index": 0}),
        _ex(
            lesson_id,
            2,
            "phrases",
            "Устойчивое выражение: «как дела?»",
            {"options": ["How are you?", "What are you?", "Where are you?", "Who are you?"], "correct_index": 0},
        ),
        _ex(lesson_id, 3, "translate", "Переведите: «спасибо»", {"options": ["thanks / thank you", "please", "sorry", "welcome"], "correct_index": 0}),
        _ex(lesson_id, 4, "words", "Слово «dictionary» — это…", {"options": ["словарь", "тетрадь", "карта", "газета"], "correct_index": 0}),
        _ex(
            lesson_id,
            5,
            "phrases",
            "Выберите нейтральное приветствие.",
            {"options": ["Hello, nice to meet you.", "Go away.", "Shut up.", "I hate you."], "correct_index": 0},
        ),
    ]


def build_reading_exercises(lesson_id: int, level: str, sub: int) -> list[Exercise]:
    # Определяем индекс текста (0..4)
    text_idx = (sub - 1) % 5

    # ---- Вопросы для уровня A1 ----
    a1_questions = {
        0: [  # "My name is Tom. I am from London. I am a student. I like coffee and books."
            ("Как зовут главного героя?", ["Tom", "Anna", "Peter", "John"], 0),
            ("Откуда он родом?", ["из Лондона", "из Парижа", "из Берлина", "из Мадрида"], 0),
            ("Что он любит?", ["кофе и книги", "чай и газеты", "молоко и пиццу", "воду и яблоки"], 0),
        ],
        1: [  # "Anna works in a small shop. The shop is open every day. Customers buy fruit and bread."
            ("Где работает Анна?", ["в маленьком магазине", "в больнице", "в школе", "в офисе"], 0),
            ("Что покупают клиенты?", ["фрукты и хлеб", "молоко и яйца", "мясо и сыр", "овощи и рыбу"], 0),
            ("Когда магазин открыт?", ["каждый день", "только по выходным", "по будням", "по вечерам"], 0),
        ],
        2: [  # "It is Sunday. The family is at home. They cook lunch and watch a funny film."
            ("Какой сегодня день?", ["воскресенье", "суббота", "понедельник", "пятница"], 0),
            ("Что делает семья?", ["готовит обед и смотрит фильм", "работает в саду", "ходит в гости", "играет в игры"], 0),
            ("Какой фильм они смотрят?", ["смешной", "грустный", "страшный", "скучный"], 0),
        ],
        3: [  # "Peter has a dog. The dog likes long walks in the park. Peter is happy after the walk."
            ("Кто есть у Питера?", ["собака", "кошка", "попугай", "хомяк"], 0),
            ("Что любит собака?", ["длинные прогулки", "короткие пробежки", "плавать", "спать"], 0),
            ("Как чувствует себя Питер после прогулки?", ["счастлив", "устал", "грустен", "сердит"], 0),
        ],
        4: [  # "Our classroom is big. There are twelve chairs. The teacher writes on the board."
            ("Сколько стульев в классе?", ["двенадцать", "десять", "пятнадцать", "восемь"], 0),
            ("Что делает учитель?", ["пишет на доске", "читает книгу", "разговаривает с учениками", "проверяет тетради"], 0),
            ("Класс большой или маленький?", ["большой", "маленький", "средний", "очень маленький"], 0),
        ],
    }

    # ---- Вопросы для уровня A2 ----
    a2_questions = {
        0: [  # "Last weekend we visited a museum in the city centre. The tickets were cheap and the guide explained everything clearly."
            ("Куда они ходили в прошлые выходные?", ["в музей", "в парк", "в кино", "в театр"], 0),
            ("Билеты были ...", ["дешёвыми", "дорогими", "бесплатными", "очень дорогими"], 0),
            ("Кто объяснял всё понятно?", ["гид", "учитель", "друг", "родители"], 0),
        ],
        1: [  # "Maria is learning English because she wants a better job. She studies for one hour after work every evening."
            ("Почему Мария учит английский?", ["хочет лучшую работу", "хочет переехать", "любит фильмы", "для путешествий"], 0),
            ("Сколько времени она занимается каждый вечер?", ["один час", "два часа", "полчаса", "три часа"], 0),
            ("Когда она занимается?", ["после работы", "утром", "в обед", "перед сном"], 0),
        ],
        2: [  # "The weather was bad yesterday, so we stayed inside. Today the sun is shining and we will go cycling."
            ("Какая погода была вчера?", ["плохая", "хорошая", "солнечная", "ветреная"], 0),
            ("Что они делали вчера?", ["оставались дома", "ходили в парк", "ездили на велосипеде", "купались"], 0),
            ("Что они будут делать сегодня?", ["кататься на велосипеде", "смотреть телевизор", "работать", "читать"], 0),
        ],
        3: [  # "If you want healthy food, try this café. They use fresh vegetables and they do not add much sugar."
            ("Что рекомендуется попробовать?", ["это кафе", "ресторан", "домашнюю еду", "фастфуд"], 0),
            ("Что используют в кафе?", ["свежие овощи", "замороженные продукты", "консервы", "полуфабрикаты"], 0),
            ("Чего они не добавляют?", ["много сахара", "соль", "масло", "специи"], 0),
        ],
        4: [  # "The train was late, but we still arrived before the meeting. Next time we will leave earlier."
            ("Что случилось с поездом?", ["опоздал", "пришёл рано", "отменили", "попал в аварию"], 0),
            ("Они всё равно успели ...", ["до встречи", "на обед", "на поезд", "домой"], 0),
            ("Что они сделают в следующий раз?", ["выйдут раньше", "поедут на такси", "не поедут", "возьмут билеты заранее"], 0),
        ],
    }

    # ---- Вопросы для уровня B1 ----
    b1_questions = {
        0: [  # "Although the project faced several delays, the team delivered a working prototype before the deadline..."
            ("С какими проблемами столкнулся проект?", ["с задержками", "с бюджетом", "с персоналом", "с технологиями"], 0),
            ("Что команда успела сделать до дедлайна?", ["работающий прототип", "финальный отчёт", "презентацию", "тестирование"], 0),
            ("Что оценили заинтересованные стороны?", ["прозрачную коммуникацию", "быстроту", "дешевизну", "красоту"], 0),
        ],
        1: [  # "Many young people choose online courses because they can study at their own pace. However, self-discipline remains essential."
            ("Почему молодые люди выбирают онлайн-курсы?", ["могут учиться в своём темпе", "они бесплатные", "они короче", "их легко пройти"], 0),
            ("Что остаётся важным?", ["самодисциплина", "хороший интернет", "мотивация", "поддержка учителя"], 0),
            ("Какое слово противопоставляет идеи?", ["However", "Because", "Although", "Therefore"], 0),
        ],
        2: [  # "The article discusses how social media affects attention spans. Critics argue that constant notifications fragment concentration."
            ("Что обсуждается в статье?", ["влияние соцсетей на концентрацию", "польза соцсетей", "история соцсетей", "безопасность в соцсетях"], 0),
            ("Что фрагментирует концентрацию?", ["постоянные уведомления", "длинные посты", "видеоролики", "лайки"], 0),
            ("Кто высказывает критику?", ["критики", "авторы", "пользователи", "учёные"], 0),
        ],
        3: [  # "Renewable energy is becoming cheaper, yet infrastructure investment is still uneven across regions."
            ("Что становится дешевле?", ["возобновляемая энергия", "ископаемое топливо", "электричество", "транспорт"], 0),
            ("Что всё ещё неравномерно?", ["инвестиции в инфраструктуру", "цены на энергию", "доступ к технологиям", "образование"], 0),
            ("Какое слово связывает противопоставление?", ["yet", "so", "because", "if"], 0),
        ],
        4: [  # "Working from home offers flexibility, but it can blur boundaries between personal life and work."
            ("Что даёт удалённая работа?", ["гибкость", "высокую зарплату", "больше свободного времени", "меньше стресса"], 0),
            ("Какой недостаток упоминается?", ["стирает границы между жизнью и работой", "требует много техники", "трудно общаться", "долгие часы"], 0),
            ("Какое слово указывает на противопоставление?", ["but", "and", "so", "because"], 0),
        ],
    }

    # ---- Вопросы для уровня B2 (пример) ----
    b2_questions = {
        0: [  # "Had the negotiations failed, the company would have faced substantial losses; fortunately, a compromise was reached..."
            ("Что случилось бы, если бы переговоры провалились?", ["компания понесла бы большие потери", "компания бы закрылась", "цены бы выросли", "людей бы уволили"], 0),
            ("Что было достигнуто в итоге?", ["компромисс", "победа", "разрыв отношений", "новый контракт"], 0),
            ("Какое слово показывает облегчение?", ["fortunately", "however", "moreover", "therefore"], 0),
        ],
        1: [  # "Not only does regular exercise improve physical health, but it also appears to benefit cognitive performance..."
            ("Что улучшает регулярная физическая нагрузка?", ["физическое здоровье и когнитивные способности", "только настроение", "только мышцы", "только сердце"], 0),
            ("Какая конструкция используется для усиления?", ["Not only... but also", "Either... or", "Neither... nor", "Both... and"], 0),
            ("Что ещё упоминается?", ["когнитивные способности", "социальные связи", "продолжительность жизни", "качество сна"], 0),
        ],
        2: [  # "The novel subtly critiques consumer culture without resorting to overt moralising, which many readers find refreshing."
            ("Что критикует роман?", ["потребительскую культуру", "политику", "религию", "образование"], 0),
            ("Как он это делает?", ["тонко, без откровенной морализации", "прямо и агрессивно", "через юмор", "через трагедию"], 0),
            ("Что находят читатели?", ["освежающим", "скучным", "сложным", "предсказуемым"], 0),
        ],
        3: [  # "Little did we realise at the time how profoundly the policy would reshape the industry within a decade."
            ("Что мы не осознавали в то время?", ["насколько политика изменит индустрию", "что политика будет принята", "кто её придумал", "когда она вступит в силу"], 0),
            ("Какая инверсия используется?", ["Little did we realise", "Did we little realise", "We did little realise", "Realise did we little"], 0),
            ("За какой период изменилась индустрия?", ["в течение десятилетия", "за год", "за месяц", "за пять лет"], 0),
        ],
        4: [  # "Such was the demand for tickets that the website crashed within minutes of the sale opening."
            ("Что вызвало ажиотаж?", ["спрос на билеты", "цена билетов", "новый фильм", "концерт"], 0),
            ("Что случилось с сайтом?", ["он упал (crash)", "работал медленно", "завис", "показал ошибку"], 0),
            ("Когда это произошло?", ["в течение нескольких минут после старта продаж", "через час", "на следующий день", "перед началом"], 0),
        ],
    }

    # ---- Вопросы для уровня C1 ----
    c1_questions = {
        0: [  # "The essay contends that ostensibly neutral algorithms may encode biases inherited from training data..."
            ("Что утверждает эссе?", ["алгоритмы могут кодировать предубеждения", "алгоритмы всегда нейтральны", "данные не влияют", "искусственный интеллект безопасен"], 0),
            ("Что наследуют алгоритмы?", ["предубеждения из обучающих данных", "скорость", "точность", "сложность"], 0),
            ("Под видом чего это происходит?", ["объективности", "эффективности", "прозрачности", "надёжности"], 0),
        ],
        1: [  # "Were policymakers to internalise the full externalities of carbon-intensive industries, fiscal instruments would arguably need recalibration."
            ("Что должны сделать политики?", ["интернализировать экстерналии", "повысить налоги", "закрыть производства", "снизить выбросы"], 0),
            ("Что потребует перекалибровки?", ["фискальные инструменты", "экологические стандарты", "торговые соглашения", "субсидии"], 0),
            ("Какая грамматическая конструкция использована?", ["инверсия (Were policymakers to...)", "пассивный залог", "условное предложение 1 типа", "сослагательное наклонение"], 0),
        ],
        2: [  # "Seldom has public discourse been so polarised, yet there remain pockets of cross-partisan collaboration worth amplifying."
            ("Как описывается публичный дискурс?", ["поляризован", "единообразен", "конструктивен", "поверхностен"], 0),
            ("Что ещё существует?", ["островки межпартийного сотрудничества", "полное согласие", "абсолютное несогласие", "нейтралитет"], 0),
            ("Какое слово указывает на контраст?", ["yet", "seldom", "so", "worth"], 0),
        ],
        3: [  # "So intricate is the interplay between migration, labour markets, and housing policy that single-factor explanations invariably fall short."
            ("Что очень сложно переплетено?", ["миграция, рынки труда и жилищная политика", "экономика и политика", "образование и здравоохранение", "экология и транспорт"], 0),
            ("Почему однопричинные объяснения недостаточны?", ["из-за сложности взаимодействия", "потому что данных мало", "из-за политических причин", "из-за отсутствия моделей"], 0),
            ("Какая конструкция используется?", ["инверсия с So intricate", "пассив", "условное придаточное", "причастный оборот"], 0),
        ],
        4: [  # "Not until the longitudinal study had been replicated did the medical community treat the findings as conclusive."
            ("Когда медицинское сообщество признало результаты?", ["только после того, как исследование было повторено", "сразу после публикации", "никогда", "через год"], 0),
            ("Какое слово указывает на временное условие?", ["Not until", "After", "Before", "When"], 0),
            ("Что потребовалось для подтверждения?", ["репликация исследования", "больше данных", "экспертная оценка", "финансирование"], 0),
        ],
    }

    # Собираем словарь уровней
    questions_by_level = {
        "A1": a1_questions,
        "A2": a2_questions,
        "B1": b1_questions,
        "B2": b2_questions,
        "C1": c1_questions,
    }

    # Если уровень не найден или индекс текста отсутствует – используем старые общие вопросы
    if level not in questions_by_level or text_idx not in questions_by_level[level]:
        # fallback (общие вопросы)
        return [
            _ex(lesson_id, 1, "reading_comp",
                "О чём главным образом идёт речь в тексте?",
                {"options": ["О повседневной ситуации или описании.", "О космосе.", "О спорте.", "Только о числах."], "correct_index": 0}),
            _ex(lesson_id, 2, "reading_comp",
                "Какой тон у текста?",
                {"options": ["Нейтральный/информативный", "Агрессивный", "Вопросительный", "Список имён"], "correct_index": 0}),
            _ex(lesson_id, 3, "reading_comp",
                "Выберите верное утверждение.",
                {"options": ["В тексте есть конкретные детали.", "В тексте нет слов.", "Текст только из цифр.", "Текст не связан с темой."], "correct_index": 0}),
        ]

    # Берём три вопроса для этого текста
    q1, o1, c1 = questions_by_level[level][text_idx][0]
    q2, o2, c2 = questions_by_level[level][text_idx][1]
    q3, o3, c3 = questions_by_level[level][text_idx][2]

    return [
        _ex(lesson_id, 1, "reading_comp", q1, {"options": o1, "correct_index": c1}),
        _ex(lesson_id, 2, "reading_comp", q2, {"options": o2, "correct_index": c2}),
        _ex(lesson_id, 3, "reading_comp", q3, {"options": o3, "correct_index": c3}),
    ]

def build_writing_exercise(lesson_id: int, level: str, sub: int) -> list[Exercise]:
    topic, min_w, keys = _writing_topic(level, sub)
    return [
        _ex(
            lesson_id,
            1,
            "writing",
            topic,
            {"min_words": min_w, "keywords": keys, "level": level},
        )
    ]


def build_listening_exercises(lesson_id: int, level: str, sub: int) -> list[Exercise]:
    out: list[Exercise] = []
    for i in range(4):
        w = _listening_word(level, sub, i)
        out.append(
            _ex(
                lesson_id,
                i + 1,
                "listening",
                f"Нажмите «Прослушать» и введите услышанное английское слово (уровень {level}).",
                {"word": w, "language": "en-US"},
            )
        )
    return out


def build_exam_exercises(lesson_id: int, level: str) -> list[Exercise]:
    """Итоговый экзамен уровня — смешанные задания."""
    ex: list[Exercise] = []
    n = 1
    pairs = [
        ("translate", "Выберите правильный перевод «возможность»", {"options": ["opportunity", "opposite", "optional", "opera"], "correct_index": 0}),
        ("words", "Слово «achieve» ближе всего к…", {"options": ["достигать", "терять", "прятать", "ломать"], "correct_index": 0}),
        ("phrases", "Вежливый отказ: «Извините, я не могу»", {"options": ["I'm sorry, I can't.", "I hate you.", "Go away.", "Shut the door."], "correct_index": 0}),
        ("reorder", "Соберите: «Она изучает английский каждый день.»", {"tokens": ["She", "studies", "English", "every", "day", "."]}),
        ("translate", "Выберите: «по сравнению с»", {"options": ["compared to / compared with", "because of me", "instead you", "according at"], "correct_index": 0}),
        ("reading_comp", "Логическое понимание: что помогает учить язык регулярно?", {"options": ["Постоянная практика и ясные цели.", "Только смотреть телевизор без звука.", "Учить один день в год.", "Игнорировать грамматику полностью."], "correct_index": 0}),
        ("words", "Слово «evidence» — это…", {"options": ["доказательство", "экран", "коридор", "подушка"], "correct_index": 0}),
        ("phrases", "Как сказать «я согласен» нейтрально?", {"options": ["I agree.", "I am agree.", "I agreeing.", "I agreeding."], "correct_index": 0}),
        ("reorder", "Соберите: «Мы должны закончить проект вовремя.»", {"tokens": ["We", "must", "finish", "the", "project", "on", "time", "."]}),
        ("translate", "Выберите правильно: «если бы я знал» (начало B2+)", {"options": ["If I knew…", "If I know…", "If I am knowing…", "If I will know…"], "correct_index": 0}),
        ("listening", "Прослушайте и введите слово.", {"word": "practice", "language": "en-US"}),
        ("reading_comp", "Зачем нужен итоговый тест уровня?", {"options": ["Чтобы проверить навыки перед следующим уровнем.", "Чтобы удалить аккаунт.", "Чтобы выключить интернет.", "Чтобы избегать практики."], "correct_index": 0}),
    ]
    for kind, prompt, payload in pairs:
        ex.append(_ex(lesson_id, n, kind, prompt, payload))
        n += 1
    return ex


def _lesson_title(level: str, aspect: str, sub: int, order: int) -> str:
    names = {
        "grammar": "Грамматика",
        "vocabulary": "Словарь",
        "reading": "Чтение",
        "writing": "Письмо",
        "listening": "Аудирование",
        "exam": "Экзамен",
    }
    if aspect == "exam":
        return f"{level} · Итоговый экзамен уровня"
    return f"{level} · {names.get(aspect, aspect)} · часть {sub}"


def seed_full_curriculum() -> None:
    if db.session.scalar(select(func.count()).select_from(Level)) > 0:
        return

    level_rows = [
        ("A1", "Начальный (A1)", "Базовые слова и простые конструкции.", 1),
        ("A2", "Элементарный (A2)", "Повседневные темы и прошедшее время.", 2),
        ("B1", "Средний (B1)", "Свободнее в разговоре, больше лексики.", 3),
        ("B2", "Продвинутый средний (B2)", "Сложные тексты и точные формулировки.", 4),
        ("C1", "Продвинутый (C1)", "Тонкости языка и академический стиль.", 5),
    ]
    for code, title, desc, so in level_rows:
        db.session.add(Level(code=code, title=title, description=desc, sort_order=so))
    db.session.commit()

    levels = db.session.scalars(select(Level).order_by(Level.sort_order)).all()
    for lv in levels:
        lc = lv.code
        for order in range(1, LESSONS_PER_LEVEL + 1):
            aspect = _aspect_for_order(order)
            sub = _sub_index(order)
            theory = ""
            passage = None
            if aspect == "grammar":
                theory = _grammar_theory(lc, sub)
            elif aspect == "vocabulary":
                theory = f"<p><strong>Словарь · {lc} · блок {sub}</strong></p><p>Запоминайте слова и устойчивые фразы — они пригодятся в чтении, аудировании и письме.</p>"
            elif aspect == "reading":
                theory = f"<p><strong>Чтение · {lc} · блок {sub}</strong></p><p>Прочитайте текст и ответьте на вопросы — так проверяется понимание, как на экзамене.</p>"
                passage = _reading_passage(lc, sub)
            elif aspect == "writing":
                theory = f"<p><strong>Письмо · {lc} · блок {sub}</strong></p><p>Напишите ответ на тему. Сайт оценит длину, ключевые слова и базовую связность текста.</p>"
            elif aspect == "listening":
                theory = f"<p><strong>Аудирование · {lc} · блок {sub}</strong></p><p>Нажимайте «Прослушать» и вводите услышанное слово. Используется синтез речи браузера (английский).</p>"

            lesson = Lesson(
                level_id=lv.id,
                order_index=order,
                aspect=aspect,
                title=_lesson_title(lc, aspect, sub, order),
                theory=theory,
                reading_passage=passage,
                is_exam=False,
            )
            db.session.add(lesson)
            db.session.flush()

            if aspect == "grammar":
                exercises = build_grammar_exercises(lesson.id, lc, sub)
            elif aspect == "vocabulary":
                exercises = build_vocab_exercises(lesson.id, lc, sub)
            elif aspect == "reading":
                exercises = build_reading_exercises(lesson.id, lc, sub)
            elif aspect == "writing":
                exercises = build_writing_exercise(lesson.id, lc, sub)
            else:
                exercises = build_listening_exercises(lesson.id, lc, sub)

            db.session.add_all(exercises)

        exam = Lesson(
            level_id=lv.id,
            order_index=EXAM_ORDER,
            aspect="exam",
            title=_lesson_title(lc, "exam", 1, EXAM_ORDER),
            theory="<p><strong>Итоговый экзамен уровня.</strong></p><p>Ответьте на все задания. После успешного прохождения откроется следующий уровень.</p>",
            reading_passage=None,
            is_exam=True,
        )
        db.session.add(exam)
        db.session.flush()
        db.session.add_all(build_exam_exercises(exam.id, lc))

    db.session.commit()


def refresh_grammar_theory() -> None:
    """
    Обновляет теорию для уже существующих грамматических уроков.
    Нужна, чтобы после изменений текста не удалять базу.
    """
    levels = db.session.scalars(select(Level).order_by(Level.sort_order)).all()
    by_level = {lv.id: lv.code for lv in levels}
    lessons = db.session.scalars(
        select(Lesson).where(Lesson.aspect == "grammar").order_by(Lesson.level_id, Lesson.order_index)
    ).all()
    changed = 0
    for lesson in lessons:
        code = by_level.get(lesson.level_id)
        if not code:
            continue
        sub = _sub_index(lesson.order_index)
        text = _grammar_theory(code, sub)
        if lesson.theory != text:
            lesson.theory = text
            changed += 1
    if changed:
        db.session.commit()


def refresh_grammar_lessons() -> None:
    """Обновляет упражнения в существующих grammar-уроках без пересоздания БД."""
    levels = db.session.scalars(select(Level).order_by(Level.sort_order)).all()
    by_level = {lv.id: lv.code for lv in levels}
    lessons = db.session.scalars(
        select(Lesson).where(Lesson.aspect == "grammar").order_by(Lesson.level_id, Lesson.order_index)
    ).all()
    changed = 0
    for lesson in lessons:
        level_code = by_level.get(lesson.level_id)
        if not level_code:
            continue
        sub = _sub_index(lesson.order_index)
        expected = build_grammar_exercises(lesson.id, level_code, sub)
        existing = db.session.scalars(
            select(Exercise).where(Exercise.lesson_id == lesson.id).order_by(Exercise.order_index)
        ).all()
        for i in range(min(5, len(existing), len(expected))):
            ex = existing[i]
            src = expected[i]
            if ex.kind != src.kind or ex.prompt != src.prompt or ex.payload_json != src.payload_json:
                ex.kind = src.kind
                ex.prompt = src.prompt
                ex.payload_json = src.payload_json
                ex.order_index = src.order_index
                changed += 1
    if changed:
        db.session.commit()
