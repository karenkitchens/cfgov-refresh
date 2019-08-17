from wagtail.wagtailcore import blocks


class QuizAnswers(blocks.StructBlock):
    answers = blocks.ListBlock(
        blocks.StructBlock([
            ('choice_letter', blocks.CharBlock(max_length=20)),
            ('answer_choice', blocks.CharBlock(max_length=500)),
            ('answer_response', blocks.RichTextBlock(
                features=[
                    'ol', 'ul', 'bold', 'italic', 'link', 'document-link'
                ],
                blank=True,
                required=False,
            )),
        ]))

    class Meta:
        template = 'paying_for_college/quiz-answers.html'


class GuidedQuiz(blocks.StructBlock):
    situation = blocks.RichTextBlock(
        features=[
            'ol', 'ul', 'bold', 'italic', 'link', 'document-link'
        ],
        blank=True,
        required=False,
    )
    questions = blocks.ListBlock(
        blocks.StructBlock([
            ('question', blocks.CharBlock(max_length=500)),
            ('answers', QuizAnswers()),
        ]))

    class Meta:
        icon = 'grip'
        template = 'paying_for_college/quiz.html'
        label = 'Guided Quiz'
