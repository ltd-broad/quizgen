from jinja2 import Environment, FileSystemLoader, select_autoescape

from .schemas import Quiz


def render_quiz_to_html(
    quiz: Quiz,
    transcript: str | None = None,
    include_transcript: bool = False,
) -> str:
    """
    Render quiz to HTML.

    We pass transcript separately (not as part of the Quiz schema)
    so instructors can optionally include it in the final embed output.
    """
    env = Environment(
        loader=FileSystemLoader("templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )
    tpl = env.get_template("quiz_spartan.html.j2")
    return tpl.render(
        quiz=quiz,
        transcript=transcript or "",
        include_transcript=bool(include_transcript),
    )
