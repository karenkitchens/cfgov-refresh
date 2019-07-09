from __future__ import unicode_literals

from wagtail.wagtailadmin.edit_handlers import (
    ObjectList, StreamFieldPanel, TabbedInterface
)
from wagtail.wagtailcore import blocks
from wagtail.wagtailcore.fields import StreamField

from v1.atomic_elements import molecules, organisms
from v1.models import CFGOVPage, CFGOVPageManager


class StudentResourcesPage(CFGOVPage):
    """A page to serve subpages of payint-for-college."""
    header = StreamField([
        ('text_introduction', molecules.TextIntroduction()),
        ('featured_content', organisms.FeaturedContent()),
    ], blank=True)

    content = StreamField([
        ('full_width_text', organisms.FullWidthText()),
        ('info_unit_group', organisms.InfoUnitGroup()),
        ('expandable_group', organisms.ExpandableGroup()),
        ('expandable', organisms.Expandable()),
        ('well', organisms.Well()),
        ('raw_html_block', blocks.RawHTMLBlock(
            label='Raw HTML block'
        )),
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
    template = 'paying_for_college/repaying-student-debt.html'

    @property
    def page_js(self):
        return (super(
            StudentResourcesPage, self).page_js + ['secondary-navigation.js']
        )
