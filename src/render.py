# src/render.py
from jinja2 import Environment, FileSystemLoader, select_autoescape
from .schemas import Quiz

def render_quiz_to_html(quiz: Quiz) -> str:
    env = Environment(
        loader=FileSystemLoader("templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )
    tpl = env.get_template("quiz_spartan.html.j2")
    return tpl.render(quiz=quiz)