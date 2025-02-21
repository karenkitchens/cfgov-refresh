from __future__ import unicode_literals

from wagtail.wagtailadmin.edit_handlers import (
    ObjectList, StreamFieldPanel, TabbedInterface
)
from wagtail.wagtailcore import blocks
from wagtail.wagtailcore.fields import StreamField

from paying_for_college.blocks import GuidedQuiz

from v1.atomic_elements import molecules, organisms
from v1.models import CFGOVPage, CFGOVPageManager


class PayingForCollegePage(CFGOVPage):
    """A base class for our suite of PFC pages."""
    header = StreamField([
        ('text_introduction', molecules.TextIntroduction()),
        ('featured_content', organisms.FeaturedContent()),
    ], blank=True)

    content_panels = CFGOVPage.content_panels + [
        StreamFieldPanel('header'),
        StreamFieldPanel('content'),
    ]
    # Tab handler interface
    edit_handler = TabbedInterface([
        ObjectList(content_panels, heading='General Content'),
        ObjectList(CFGOVPage.sidefoot_panels, heading='Sidebar'),
        ObjectList(CFGOVPage.settings_panels, heading='Configuration'),
    ])
    objects = CFGOVPageManager()

    class Meta:
        abstract = True


class PayingForCollegeContent(blocks.StreamBlock):
    """A base content block for PFC pages."""
    full_width_text = organisms.FullWidthText()
    info_unit_group = organisms.InfoUnitGroup()
    expandable_group = organisms.ExpandableGroup()
    expandable = organisms.Expandable()
    well = organisms.Well()
    raw_html_block = blocks.RawHTMLBlock(label='Raw HTML block')


class StudentLoanQuizContent(PayingForCollegeContent):
    guided_quiz = GuidedQuiz()


class StudentLoanQuizPage(PayingForCollegePage):
    """A page to guide students through the college debt maze."""
    content = StreamField(StudentLoanQuizContent, blank=True)

    def get_template(self, request):
        for block in self.content:
            block.value['situation_id'] = block.id
        return 'paying-for-college/choose-a-student-loan.html'


class CollegeCostsPage(PayingForCollegePage):
    """Breaking down financial aid and loans for prospective students."""
    content = StreamField(PayingForCollegeContent, blank=True)

    def get_template(self, request):
        return 'paying-for-college/college-costs.html'


class RepayingStudentDebtPage(PayingForCollegePage):
    """A page to serve static subpages in the paying-for-college suite."""
    content = StreamField(PayingForCollegeContent, blank=True)

    def get_template(self, request):
        return 'paying-for-college/repaying-student-debt.html'
