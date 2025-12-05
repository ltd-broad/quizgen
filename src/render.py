from jinja2 import Environment, FileSystemLoader, select_autoescape

from .schemas import Quiz


def render_quiz_to_html(
    quiz: Quiz,
    transcript: str | None = None,
    include_transcript: bool = False,
    include_intro: bool = True,
) -> str:
    """Render the quiz (and optional transcript/intro) to HTML using the Spartan template."""
    env = Environment(
        loader=FileSystemLoader("templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )
    tpl = env.get_template("quiz_spartan.html.j2")
    return tpl.render(
        quiz=quiz,
        transcript=transcript,
        include_transcript=include_transcript,
        include_intro=include_intro,
    )
