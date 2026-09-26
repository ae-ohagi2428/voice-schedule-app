from django.conf import settings
from openai import OpenAI


def ask_ai(text):
    client = OpenAI()

    response = client.responses.create(
        model=settings.OPENAI_MODEL,
        instructions="受け取った文章を、丁寧な言葉に直して返してください。",
        input=text,
        reasoning={'effort': 'low'},
    )
    return response.output_text