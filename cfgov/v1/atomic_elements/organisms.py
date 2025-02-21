import itertools
import json
from collections import Counter
from functools import partial
from six import string_types as basestring
from six.moves.urllib.parse import urlencode

from django import forms
from django.apps import apps
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.forms.utils import ErrorList
from django.template.loader import render_to_string
from django.utils.encoding import smart_text
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe

from wagtail.contrib.table_block.blocks import TableBlock
from wagtail.utils.widgets import WidgetWithScript
from wagtail.wagtailcore import blocks
from wagtail.wagtailcore.models import Page
from wagtail.wagtailcore.rich_text import DbWhitelister, expand_db_html
from wagtail.wagtaildocs.blocks import DocumentChooserBlock
from wagtail.wagtailimages import blocks as images_blocks
from wagtail.wagtailsnippets.blocks import SnippetChooserBlock

from jinja2 import Markup
from taggit.models import Tag

import ask_cfpb
from v1 import blocks as v1_blocks
from v1.atomic_elements import atoms, molecules
from v1.util import ref


class AskSearch(blocks.StructBlock):
    show_label = blocks.BooleanBlock(
        default=True,
        required=False,
        help_text='Whether to show form label.'
    )

    placeholder = blocks.TextBlock(
        required=False,
        help_text='Text to show for the input placeholder text.'
    )

    class Meta:
        icon = 'search'
        template = '_includes/organisms/ask-search.html'

    class Media:
        js = ['ask-autocomplete.js']


class Well(blocks.StructBlock):
    content = blocks.RichTextBlock(required=False, label='Well')

    class Meta:
        icon = 'placeholder'
        template = '_includes/organisms/well.html'


class WellWithAskSearch(Well):
    ask_search = AskSearch()


class InfoUnitGroup(blocks.StructBlock):
    format = blocks.ChoiceBlock(
        choices=[
            ('50-50', '50/50'),
            ('33-33-33', '33/33/33'),
            ('25-75', '25/75'),
        ],
        default='50-50',
        label='Format',
        help_text='Choose the number and width of info unit columns.',
    )

    heading = v1_blocks.HeadingBlock(required=False)

    intro = blocks.RichTextBlock(
        required=False,
        help_text='If this field is not empty, '
                  'the Heading field must also be set.'
    )

    link_image_and_heading = blocks.BooleanBlock(
        default=True,
        required=False,
        help_text=('Check this to link all images and headings to the URL of '
                   'the first link in their unit\'s list, if there is a link.')
    )

    has_top_rule_line = blocks.BooleanBlock(
        default=False,
        required=False,
        help_text=('Check this to add a horizontal rule line to top of '
                   'info unit group.')
    )

    lines_between_items = blocks.BooleanBlock(
        default=False,
        required=False,
        label='Show rule lines between items',
        help_text=('Check this to show horizontal rule lines between info '
                   'units.')
    )

    info_units = blocks.ListBlock(molecules.InfoUnit())

    sharing = blocks.StructBlock([
        ('shareable', blocks.BooleanBlock(label='Include sharing links?',
                                          help_text='If checked, share links '
                                                    'will be included below '
                                                    'the items.',
                                          required=False)),
        ('share_blurb', blocks.CharBlock(help_text='Sets the tweet text, '
                                                   'email subject line, and '
                                                   'LinkedIn post text.',
                                         required=False)),
    ])

    def clean(self, value):
        cleaned = super(InfoUnitGroup, self).clean(value)

        # Intro paragraph may only be specified with a heading.
        if cleaned.get('intro') and not cleaned.get('heading'):
            raise ValidationError(
                'Validation error in InfoUnitGroup: intro with no heading',
                params={'heading': ErrorList([
                    'Required if paragraph is not empty. (If it looks empty, '
                    'click into it and hit the delete key a bunch of times.)'
                ])}
            )

        # If 25/75, info units must have images.
        if cleaned.get('format') == '25-75':
            for unit in cleaned.get('info_units'):
                if not unit['image']['upload']:
                    raise ValidationError(
                        ('Validation error in InfoUnitGroup: '
                         '25-75 with no image'),
                        params={'format': ErrorList([
                            'Info units must include images when using the '
                            '25/75 format. Search for an "FPO" image if you '
                            'need a temporary placeholder.'
                        ])}
                    )

        return cleaned

    class Meta:
        icon = 'list-ul'
        template = '_includes/organisms/info-unit-group-2.html'


class PostPreviewSnapshot(blocks.StructBlock):
    limit = blocks.CharBlock(default='3', label='Limit',
                             help_text='How many posts do you want to show?')

    post_date_description = blocks.CharBlock(default='Published')

    class Meta:
        icon = 'order'
        template = '_includes/organisms/post-preview-snapshot.html'


class EmailSignUp(blocks.StructBlock):
    heading = blocks.CharBlock(required=False, default='Stay informed')
    default_heading = blocks.BooleanBlock(
        required=False,
        default=True,
        label='Default heading style',
        help_text=('If selected, heading will be styled as an H5 '
                   'with green top rule. Deselect to style header as H3.')
    )
    text = blocks.CharBlock(
        required=False,
        help_text=('Write a sentence or two about what kinds of emails the '
                   'user is signing up for, how frequently they will be sent, '
                   'etc.')
    )
    gd_code = blocks.CharBlock(
        required=False,
        label='GovDelivery code',
        help_text=('Code for the topic (i.e., mailing list) you want people '
                   'who submit this form to subscribe to. Format: USCFPB_###')
    )
    disclaimer_page = blocks.PageChooserBlock(
        required=False,
        label='Privacy Act statement',
        help_text=('Choose the page that the "See Privacy Act statement" link '
                   'should go to. If in doubt, use "Generic Email Sign-Up '
                   'Privacy Act Statement".')
    )

    class Meta:
        icon = 'mail'
        template = '_includes/organisms/email-signup.html'

    class Media:
        js = ['email-signup.js']


class RegComment(blocks.StructBlock):
    document_id = blocks.CharBlock(
        required=True,
        label='Document ID',
        help_text=('Federal Register document ID number to which the comment '
                   'should be submitted. Should follow this format: '
                   'CFPB-YYYY-####-####')
    )
    generic_regs_link = blocks.BooleanBlock(
        required=False,
        default=True,
        label='Use generic Regs.gov link?',
        help_text=('If unchecked, the link to comment at Regulations.gov if '
                   'you want to add attachments will link directly to the '
                   'document given above. Leave this checked if this comment '
                   'form is being published before the full document is live '
                   'at Regulations.gov, then uncheck it when the full '
                   'document has been published.')
    )
    id = blocks.CharBlock(
        required=False,
        label='Form ID',
        help_text=('Sets the `id` attribute in the form\'s markup. If not '
                   'set, the form will be assigned a base id of '
                   '`o-reg-comment_` with a random number appended.')
    )

    class Meta:
        icon = 'form'
        template = '_includes/organisms/reg-comment.html'


class RelatedPosts(blocks.StructBlock):
    limit = blocks.CharBlock(
        default='3',
        help_text=('This limit applies to EACH TYPE of post this module '
                   'retrieves, not the total number of retrieved posts.')
    )
    show_heading = blocks.BooleanBlock(
        required=False,
        default=True,
        label='Show Heading and Icon?',
        help_text=('This toggles the heading and '
                   'icon for the related types.')
    )
    header_title = blocks.CharBlock(
        default='Further reading',
        label='Slug Title'
    )

    relate_posts = blocks.BooleanBlock(
        required=False,
        default=True,
        label='Blog Posts',
        editable=False
    )
    relate_newsroom = blocks.BooleanBlock(
        required=False,
        default=True,
        label='Newsroom',
        editable=False
    )
    relate_events = blocks.BooleanBlock(
        required=False,
        default=True,
        label='Events'
    )

    specific_categories = blocks.ListBlock(
        blocks.ChoiceBlock(choices=ref.related_posts_categories,
                           required=False),
        required=False
    )

    and_filtering = blocks.BooleanBlock(
        required=False,
        default=False,
        label='Match all topic tags',
        help_text=('If checked, related posts will only be pulled in if they '
                   'match ALL topic tags set on this page. Otherwise, related '
                   'posts can match any one topic tag.')
    )

    alternate_view_more_url = blocks.CharBlock(
        required=False,
        label='Alternate "View more" URL',
        help_text=('By default, the "View more" link will go to the Activity '
                   'Log, filtered based on the above parameters. Enter a URL '
                   'in this field to override that link destination.')
    )

    def get_context(self, value, parent_context=None):
        context = super(RelatedPosts, self).get_context(
            value,
            parent_context=parent_context
        )

        page = context['page']
        request = context['request']

        context.update({
            'posts': self.related_posts(page, value),
            'view_more_url': (
                value['alternate_view_more_url'] or
                self.view_more_url(page, request)
            ),
        })

        return context

    @staticmethod
    def related_posts(page, value):
        from v1.models.learn_page import AbstractFilterPage

        def tag_set(related_page):
            return set([tag.pk for tag in related_page.tags.all()])

        def match_all_topic_tags(queryset, page_tags):
            """Return pages that share every one of the current page's tags."""
            current_tag_set = set([tag.pk for tag in page_tags])
            return [page for page in queryset
                    if current_tag_set.issubset(tag_set(page))]

        related_types = []
        related_items = {}
        if value.get('relate_posts'):
            related_types.append('blog')
        if value.get('relate_newsroom'):
            related_types.append('newsroom')
        if value.get('relate_events'):
            related_types.append('events')
        if not related_types:
            return related_items

        tags = page.tags.all()
        and_filtering = value['and_filtering']
        specific_categories = value['specific_categories']
        limit = int(value['limit'])
        queryset = AbstractFilterPage.objects.live().exclude(
            id=page.id).order_by('-date_published').distinct().specific()

        for parent in related_types:  # blog, newsroom or events
            # Include children of this slug that match at least 1 tag
            children = Page.objects.child_of_q(Page.objects.get(slug=parent))
            filters = children & Q(('tags__in', tags))

            if parent == 'events':
                # Include archived events matches
                archive = Page.objects.get(slug='archive-past-events')
                children = Page.objects.child_of_q(archive)
                filters |= children & Q(('tags__in', tags))

            if specific_categories:
                # Filter by any additional categories specified
                categories = ref.get_appropriate_categories(
                    specific_categories=specific_categories,
                    page_type=parent
                )
                if categories:
                    filters &= Q(('categories__name__in', categories))

            related_queryset = queryset.filter(filters)

            if and_filtering:
                # By default, we need to match at least one tag
                # If specified in the admin, change this to match ALL tags
                related_queryset = match_all_topic_tags(related_queryset, tags)

            related_items[parent.title()] = related_queryset[:limit]

        # Return items in the dictionary that have non-empty querysets
        return {key: value for key, value in related_items.items() if value}

    @staticmethod
    def view_more_url(page, request):
        """Generate a URL to see more pages like this one.
        This method generates a link to the Activity Log page (which must
        exist and must have a unique site-wide slug of "activity-log") with
        filters set by the tags assigned to this page, like this:
        /activity-log/?topics=foo&topics=bar&topics=baz
        If for some reason a page with slug "activity-log" does not exist,
        this method will raise Page.DoesNotExist.
        """
        activity_log = Page.objects.get(slug='activity-log')
        url = activity_log.get_url(request)

        tags = urlencode([('topics', tag) for tag in page.tags.slugs()])
        if tags:
            url += '?' + tags

        return url

    class Meta:
        icon = 'link'
        template = '_includes/molecules/related-posts.html'


class MainContactInfo(blocks.StructBlock):
    contact = SnippetChooserBlock('v1.Contact')
    has_top_rule_line = blocks.BooleanBlock(
        default=False,
        required=False,
        help_text='Add a horizontal rule line to top of contact block.'
    )

    class Meta:
        icon = 'wagtail'
        template = '_includes/organisms/main-contact-info.html'


class SidebarContactInfo(MainContactInfo):
    class Meta:
        template = '_includes/organisms/sidebar-contact-info.html'


class BureauStructurePosition(blocks.StructBlock):
    office_name = blocks.CharBlock()
    lead = v1_blocks.PlaceholderCharBlock(placeholder="Name")
    title = blocks.StructBlock([
        ('line_1', v1_blocks.PlaceholderCharBlock(required=False,
                                                  placeholder="Title 1")),
        ('line_2', v1_blocks.PlaceholderCharBlock(required=False,
                                                  placeholder="Title 2"))
    ])


class BureauStructureDivision(blocks.StructBlock):
    division = v1_blocks.PlaceholderCharBlock(label='Division')
    division_lead = v1_blocks.PlaceholderCharBlock(placeholder='Name')
    title = blocks.StructBlock([
        ('line_1', v1_blocks.PlaceholderCharBlock(required=False,
                                                  placeholder='Title 1')),
        ('line_2', v1_blocks.PlaceholderCharBlock(required=False,
                                                  placeholder='Title 2'))
    ])
    division_lead_1 = v1_blocks.PlaceholderCharBlock(required=False,
                                                     placeholder='Name',
                                                     label='Division Lead')
    title_1 = blocks.StructBlock([
        ('line_1', v1_blocks.PlaceholderCharBlock(required=False,
                                                  placeholder='Title 1')),
        ('line_2', v1_blocks.PlaceholderCharBlock(required=False,
                                                  placeholder='Title 2'))
    ], label='Title')
    link_to_division_page = atoms.Hyperlink(required=False)
    offices = blocks.ListBlock(BureauStructurePosition(required=False))


class BureauStructureOffice(BureauStructurePosition):
    offices = blocks.ListBlock(BureauStructurePosition(required=False))


class BureauStructure(blocks.StructBlock):
    last_updated_date = blocks.DateBlock(required=False)
    download_image = DocumentChooserBlock(icon='image', required=False)
    director = blocks.CharBlock()
    divisions = blocks.ListBlock(BureauStructureDivision())
    office_of_the_director = blocks.ListBlock(
        BureauStructureOffice(), label='Office of the Director'
    )

    class Meta:
        icon = None
        template = '_includes/organisms/bureau-structure.html'
        icon = "table"

    class Media:
        js = ['bureau-structure.js']


class RichTextTableInput(WidgetWithScript, forms.HiddenInput):
    def __init__(self, table_options=None, attrs=None):
        super(RichTextTableInput, self).__init__(attrs=attrs)
        self.table_options = table_options

    def render(self, name, value, attrs=None):
        value = self.json_dict_apply(
            value,
            partial(expand_db_html, for_editor=True)
        )

        html = super(RichTextTableInput, self).render(name, value, attrs)
        return Markup(render_to_string('wagtailadmin/table_input.html', {
            'original_field_html': html,
            'attrs': attrs,
            'value': value,
        }))

    def render_js_init(self, id_, name, value):
        return "initRichTextTable({0}, {1});".format(
            json.dumps(id_),
            json.dumps(self.table_options)
        )

    def value_from_datadict(self, data, files, name):
        value = super(RichTextTableInput, self).value_from_datadict(
            data, files, name
        )

        return self.json_dict_apply(value, DbWhitelister.clean)

    @staticmethod
    def json_dict_apply(value, callback):
        value = json.loads(value)

        for row in (value or {}).get('data') or []:
            for i, cell in enumerate(row or []):
                if cell:
                    row[i] = callback(cell)

        return json.dumps(value)


class AtomicTableBlock(TableBlock):
    @cached_property
    def field(self):
        widget = RichTextTableInput(table_options=self.table_options)
        return forms.CharField(widget=widget, **self.field_options)

    def to_python(self, value):
        new_value = super(AtomicTableBlock, self).to_python(value)
        if new_value:
            new_value['has_data'] = self.get_has_data(new_value)
        return new_value

    def get_has_data(self, value):
        has_data = False
        if value and 'data' in value:
            first_row_index = 1 if value.get('first_row_is_table_header',
                                             None) else 0
            first_col_index = 1 if value.get('first_col_is_header',
                                             None) else 0

            for row in value['data'][first_row_index:]:
                for cell in row[first_col_index:]:
                    if cell:
                        has_data = True
                        break
        return has_data

    class Meta:
        default = None
        icon = 'table'
        template = '_includes/organisms/table.html'
        label = 'Table'

    class Media:
        js = ['table.js']


class ModelBlock(blocks.StructBlock):
    """Abstract StructBlock that provides Django model instances to subclasses.

    This class inherits from the standard Wagtail StructBlock but adds helper
    methods that allow subclasses to dynamically render Django model instances.
    This is useful if, for example, a widget needs to show a list of all model
    instances meeting a certain criteria.

    Subclasses must override the 'model' class attribute with the fully-
    qualified name of the model to be used, for example 'my.app.Modelname'.

    Subclasses may optionally override the 'filter_queryset' method to do
    filtering on the model QuerySet.

    Subclasses may optionally override either the class attributes 'ordering'
    (providing a Django-style string or tuple of orderings to use) and 'limit'
    (providing an integer to use to slice the model QuerySet), or provide
    methods 'get_ordering' and 'get_limit' that do the same thing.

    """
    model = None
    ordering = None
    limit = None

    def get_queryset(self, value):
        model_cls = apps.get_model(self.model)
        qs = model_cls.objects.all()

        qs = self.filter_queryset(qs, value)

        ordering = self.get_ordering(value)
        if ordering:
            if isinstance(ordering, basestring):
                ordering = (ordering,)

            qs = qs.order_by(*ordering)

        limit = self.get_limit(value)
        if limit:
            qs = qs[:limit]

        return qs

    def filter_queryset(self, qs, value):
        return qs

    def get_ordering(self, value):
        return self.ordering

    def get_limit(self, value):
        return self.limit


class ModelTable(ModelBlock):
    """Abstract StructBlock that can generate a table from a Django model.

    Subclasses must override the 'fields' and 'field_headers' class attributes
    to specify which model fields to include in the generated table.

    By default model instance values will be converted to text for display
    in table rows. To override this, subclasses may define custom field
    formatter methods, using the name 'make_FIELD_value'. This may be useful
    if fields are non-text types, for example when formatting dates.

    For example:

        def make_created_value(self, instance, value):
            return value.strftime('%b %d, %Y')

    """
    fields = None
    field_headers = None

    first_row_is_table_header = blocks.BooleanBlock(
        required=False,
        default=True,
        help_text='Display the first row as a header.'
    )
    first_col_is_header = blocks.BooleanBlock(
        required=False,
        default=False,
        help_text='Display the first column as a header.'
    )
    is_full_width = blocks.BooleanBlock(
        required=False,
        default=False,
        help_text='Display the table at full width.'
    )
    is_striped = blocks.BooleanBlock(
        required=False,
        default=False,
        help_text='Display the table with striped rows.'
    )
    is_stacked = blocks.BooleanBlock(
        required=False,
        default=True,
        help_text='Stack the table columns on mobile.'
    )
    empty_table_msg = blocks.CharBlock(
        label='No Table Data Message',
        required=False,
        help_text='Message to display if there is no table data.'
    )

    def render(self, value, context=None):
        rows = [self.field_headers]

        rows.extend([
            self.make_row(instance) for instance in self.get_queryset(value)
        ])

        table_value = {
            'data': rows,
        }

        table_value.update((k, value.get(k)) for k in (
            'first_row_is_table_header',
            'first_col_is_header',
            'is_full_width',
            'is_striped',
            'is_stacked',
            'empty_table_msg',
        ))

        table = AtomicTableBlock()
        value = table.to_python(table_value)
        return table.render(value, context=context)

    def make_row(self, instance):
        return [
            self.make_value(instance, field)
            for field in self.fields
        ]

    def make_value(self, instance, field):
        value = getattr(instance, field)
        return self.format_field_value(instance, field, value)

    def format_field_value(self, instance, field, value):
        custom_formatter_name = 'make_{}_value'.format(field)
        custom_formatter = getattr(self, custom_formatter_name, None)

        if custom_formatter:
            return custom_formatter(instance, value)
        else:
            return smart_text(value)

    class Meta:
        icon = 'table'


class ModelList(ModelBlock):
    """Abstract StructBlock that can generate a list from a Django model.

    Subclasses must define a 'render' method that renders the model QuerySet
    to a string.

    For example:

        def render(self, value, context=None):
            value['objects'] = self.get_queryset(value)
            template = 'path/to/template.html'
            return render_to_string(template, value)

    """
    limit = atoms.IntegerBlock(
        default=5,
        label='Maximum items',
        min_value=0,
        help_text='Limit list to this number of items'
    )

    def __init__(self, *args, **kwargs):
        super(ModelList, self).__init__(*args, **kwargs)

    def get_limit(self, value):
        return value.get('limit')

    class Meta:
        icon = 'list-ul'


class FullWidthText(blocks.StreamBlock):
    content = blocks.RichTextBlock(icon='edit')
    content_with_anchor = molecules.ContentWithAnchor()
    heading = v1_blocks.HeadingBlock(required=False)
    image = molecules.ContentImage()
    table_block = AtomicTableBlock(table_options={'renderer': 'html'})
    quote = molecules.Quote()
    cta = molecules.CallToAction()
    related_links = molecules.RelatedLinks()
    reusable_text = v1_blocks.ReusableTextChooserBlock('v1.ReusableText')
    email_signup = EmailSignUp()
    well = Well()
    well_with_ask_search = WellWithAskSearch()

    class Meta:
        icon = 'edit'
        template = '_includes/organisms/full-width-text.html'


class BaseExpandable(blocks.StructBlock):
    label = blocks.CharBlock(required=False)
    is_bordered = blocks.BooleanBlock(required=False)
    is_midtone = blocks.BooleanBlock(required=False)
    is_expanded = blocks.BooleanBlock(required=False)

    class Meta:
        icon = 'list-ul'
        template = '_includes/organisms/expandable.html'
        label = 'Expandable'

    class Media:
        js = ["expandable.js"]


class Expandable(BaseExpandable):
    content = blocks.StreamBlock(
        [
            ('paragraph', blocks.RichTextBlock(required=False)),
            ('well', Well()),
            ('links', atoms.Hyperlink()),
            ('email', molecules.ContactEmail()),
            ('phone', molecules.ContactPhone()),
            ('address', molecules.ContactAddress()),
        ], blank=True
    )


class ExpandableGroup(blocks.StructBlock):
    heading = blocks.CharBlock(required=False)
    body = blocks.RichTextBlock(required=False)
    is_accordion = blocks.BooleanBlock(required=False)
    has_top_rule_line = blocks.BooleanBlock(
        default=False,
        required=False,
        help_text=('Check this to add a horizontal rule line to top of '
                   'expandable group.')
    )
    add_heading_id = blocks.BooleanBlock(default=False, required=False)

    expandables = blocks.ListBlock(Expandable())

    class Meta:
        icon = 'list-ul'
        template = '_includes/organisms/expandable-group.html'

    class Media:
        js = ["expandable-group.js"]


class ContactExpandableGroup(blocks.StructBlock):
    """Expandable group that renders selected Contact snippets."""
    group_title = blocks.CharBlock()
    contacts = blocks.ListBlock(SnippetChooserBlock('v1.Contact'))

    def get_context(self, value, parent_context=None):
        context = super(ContactExpandableGroup, self).get_context(
            value,
            parent_context=parent_context
        )

        # This block mimics the ExpandableGroup block.
        context['value'] = ExpandableGroup().to_python({
            'heading': value['group_title'],
            'add_heading_id': True,
            'expandables': [
                {
                    'label': contact.heading,
                    'content': contact.contact_info.stream_data,
                } for contact in value['contacts']
            ],
        })

        return context

    def bulk_to_python(self, values):
        """Support bulk retrieval of Contacts to reduce database queries.

        This method leverages Wagtail's undocumented method for doing bulk
        retrieval of data for StreamField blocks. It retrieves all Contacts
        referenced by a StreamField in a single lookup, instead of the
        default behavior of doing one database query per SnippetChooserBlock.
        """
        contact_ids = set(
            itertools.chain(*(block['contacts'] for block in values))
        )

        contact_model = self.child_blocks['contacts'].child_block.target_model
        contacts_by_id = contact_model.objects.in_bulk(contact_ids)

        for block in values:
            block['contacts'] = [
                contacts_by_id[contact_id]
                for contact_id in block['contacts']
            ]

        return values

    class Meta:
        icon = 'list-ul'
        template = '_includes/organisms/expandable-group.html'

    class Media:
        js = ["expandable-group.js"]


class ItemIntroduction(blocks.StructBlock):
    show_category = blocks.BooleanBlock(
        required=False,
        default=True,
        help_text=(
            "Whether to show the category or not "
            "(category must be set in 'Configuration')."
        )
    )

    heading = blocks.CharBlock(required=False)
    paragraph = blocks.RichTextBlock(required=False)

    date = blocks.DateBlock(required=False)
    has_social = blocks.BooleanBlock(
        required=False, help_text="Whether to show the share icons or not.")

    class Meta:
        icon = 'form'
        template = '_includes/organisms/item-introduction.html'
        classname = 'block__flush-top'


class FilterableList(BaseExpandable):
    title = blocks.BooleanBlock(default=True, required=False,
                                label='Filter Title')
    no_posts_message = blocks.CharBlock(
        required=False,
        help_text=mark_safe(
            'Message for the <a href="https://cfpb.github.io/'
            'capital-framework/components/cf-notifications/'
            '#recommended-notification-patterns">notification</a> '
            'that will be displayed instead of filter controls '
            'if there are no posts to filter.'))
    no_posts_explanation = blocks.CharBlock(
        required=False,
        help_text='Additional explanation for the notification that '
                  'will be displayed if there are no posts to filter.')
    post_date_description = blocks.CharBlock(
        required=False,
        label='Date stamp descriptor',
        help_text='Strongly encouraged to help users understand the '
                  'action that the date of the post is linked to, '
                  'i.e. published, issued, released.')
    categories = blocks.StructBlock([
        ('filter_category',
         blocks.BooleanBlock(default=True, required=False)),
        ('show_preview_categories',
         blocks.BooleanBlock(default=True, required=False)),
        ('page_type', blocks.ChoiceBlock(
            choices=ref.filterable_list_page_types,
            required=False
        )),
    ])
    topic_filtering = blocks.ChoiceBlock(
        choices=[
            ('no_filter', "Don't filter topics"),
            ('sort_alphabetically',
                'Filter topics, sort topic list alphabetically'),
            ('sort_by_frequency',
                'Filter topics, sort topic list by number of results'),
        ],
        required=True,
        help_text='Whether to include a dropdown in the filter controls '
                  'for "Topics"')
    authors = blocks.BooleanBlock(default=True, required=False,
                                  label='Filter Authors')
    date_range = blocks.BooleanBlock(default=True, required=False,
                                     label='Filter Date Range')
    output_5050 = blocks.BooleanBlock(default=False, required=False,
                                      label="Render preview items as 50-50s")
    link_image_and_heading = blocks.BooleanBlock(
        default=False,
        required=False,
        help_text='Add links to post preview images and'
                  ' headings in filterable list results'
    )

    class Meta:
        label = 'Filterable List'
        icon = 'form'
        template = '_includes/organisms/filterable-list.html'

    class Media:
        js = ['filterable-list.js']

    @staticmethod
    def get_filterable_topics(filterable_page_ids, value):
        """Given a set of page IDs, return the list of filterable topics"""
        tags = Tag.objects.filter(
            v1_cfgovtaggedpages_items__content_object__id__in=filterable_page_ids  # noqa E501
        ).values_list('slug', 'name')

        sort_order = value.get('topic_filtering', 'sort_by_frequency')
        if sort_order == 'sort_alphabetically':
            return tags.distinct().order_by('name')
        elif sort_order == 'sort_by_frequency':
            return [tag for (tag, _) in Counter(tags).most_common()]
        else:
            return []

    def get_context(self, value, parent_context=None):
        context = super(FilterableList, self).get_context(
            value,
            parent_context=parent_context
        )
        show_topics = value['topic_filtering'] == 'sort_by_frequency' or \
            value['topic_filtering'] == 'sort_alphabetically'
        # Different instances of FilterableList need to render their post
        # previews differently depending on the page type they live on. By
        # default post dates and tags are always shown.
        context.update({
            'show_post_dates': True,
            'show_post_tags': True,
            'show_topic_filter': show_topics,
        })

        # Pull out the page type selected when the FilterableList was
        # configured in the page editor, if one was specified. See the
        # 'categories' block definition above. The page type choices are
        # defined in v1.util.ref.page_types.
        page_type = value['categories'].get('page_type')

        # Pending a much-needed refactor of that code, this logic is being
        # placed here to keep FilterableList logic in one place. It would be
        # better if this kind of configuration lived on custom Page models.
        page_type_overrides = {
            'cfpb-researchers': {'show_post_dates': False},
            'consumer-reporting': {'show_post_dates': False},
            'foia-freq-req-record': {'show_post_tags': False},
        }

        context.update(page_type_overrides.get(page_type, {}))
        return context


class VideoPlayer(blocks.StructBlock):
    video_url = blocks.RegexBlock(
        label='YouTube Embed URL',
        default='https://www.youtube.com/embed/',
        required=True,
        regex=r'^https:\/\/www\.youtube\.com\/embed\/.+$',
        error_messages={
            'required': 'The YouTube URL field is required for video players.',
            'invalid': "The YouTube URL is in the wrong format. "
                       "You must use the embed URL "
                       "(https://www.youtube.com/embed/video_id), "
                       "which can be obtained by clicking Share > Embed "
                       "on the YouTube video page.",
        }
    )

    class Meta:
        icon = 'media'
        template = '_includes/organisms/video-player.html'

    class Media:
        js = ['video-player.js']


class FeaturedContent(blocks.StructBlock):
    heading = blocks.CharBlock(required=False)
    body = blocks.RichTextBlock(required=False)

    post = blocks.PageChooserBlock(required=False)
    show_post_link = blocks.BooleanBlock(required=False,
                                         label="Render post link?")
    post_link_text = blocks.CharBlock(required=False)

    image = atoms.ImageBasic(required=False)

    links = blocks.ListBlock(atoms.Hyperlink(required=False),
                             label='Additional Links')

    video = blocks.StructBlock([
        ('id', blocks.CharBlock(
            required=False,
            label='ID',
            help_text='E.g., in "https://www.youtube.com/watch?v=en0Iq8II4fA",'
                      ' the ID is everything after the "?v=".')),
        ('url', blocks.CharBlock(
            required=False,
            label='URL',
            help_text='You must use the embed URL, e.g., '
                      'https://www.youtube.com/embed/'
                      'JPTg8ZB3j5c?autoplay=1&enablejsapi=1')),
        ('height', blocks.CharBlock(default='320', required=False)),
        ('width', blocks.CharBlock(default='568', required=False)),
    ])

    class Meta:
        template = '_includes/organisms/featured-content.html'
        icon = 'doc-full-inverse'
        label = 'Featured Content'
        classname = 'block__flush'

    class Media:
        js = ['featured-content-module.js']


class ChartBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=True)
    # todo: make radio buttons
    chart_type = blocks.ChoiceBlock(
        choices=[
            ('bar', 'Bar | % y-axis values'),
            ('line', 'Line | millions/billions y-axis values'),
            ('line-index', 'Line-Index | integer y-axis values'),
            ('tile_map', 'Tile Map | grid-like USA map'),
        ],
        required=True
    )
    color_scheme = blocks.ChoiceBlock(
        choices=[
            ('blue', 'Blue'),
            ('gold', 'Gold'),
            ('green', 'Green'),
            ('navy', 'Navy'),
            ('neutral', 'Neutral'),
            ('purple', 'Purple'),
            ('teal', 'Teal'),
        ],
        required=False,
        help_text='Chart\'s color scheme. See '
                  '"https://github.com/cfpb/cfpb-chart-builder'
                  '#createchart-options-".')
    data_source = blocks.CharBlock(
        required=True,
        help_text='Location of the chart\'s data source relative to '
                  '"https://files.consumerfinance.gov/data/". For example,'
                  '"consumer-credit-trends/auto-loans/num_data_AUT.csv".')
    date_published = blocks.DateBlock(
        help_text='Automatically generated when CCT cron job runs'
    )
    description = blocks.CharBlock(
        required=True,
        help_text='Briefly summarize the chart for visually impaired users.')

    has_top_rule_line = blocks.BooleanBlock(
        default=False,
        required=False,
        help_text=('Check this to add a horizontal rule line to top of '
                   'chart block.')
    )

    last_updated_projected_data = blocks.DateBlock(
        help_text='Month of latest entry in dataset'
    )

    metadata = blocks.CharBlock(
        required=False,
        help_text='Optional metadata for the chart to use. '
                  'For example, with CCT this would be the chart\'s "group".')
    note = blocks.CharBlock(
        required=False,
        help_text='Text to display as a footnote. For example, '
                  '"Data from the last six months are not final."')
    y_axis_label = blocks.CharBlock(
        required=False,
        help_text='Custom y-axis label. '
                  'NOTE: Line-Index chart y-axis '
                  'is not overridable with this field!'
    )

    class Meta:
        label = 'Chart Block'
        icon = 'image'
        template = '_includes/organisms/chart.html'

    class Media:
        js = ['chart.js']


class MortgageChartBlock(blocks.StructBlock):
    content_block = blocks.RichTextBlock()
    title = blocks.CharBlock(required=True, classname="title")
    description = blocks.CharBlock(
        required=False,
        help_text='Chart summary for visually impaired users.')
    note = blocks.CharBlock(
        required=False,
        help_text='Text for "Note" section of footnotes.')
    has_top_rule_line = blocks.BooleanBlock(
        default=False,
        required=False,
        help_text=('Check this to add a horizontal rule line to top of '
                   'chart block.')
    )

    class Meta:
        label = 'Mortgage Chart Block'
        icon = 'image'
        template = '_includes/organisms/mortgage-chart.html'

    class Media:
        js = ['mortgage-performance-trends.js']


class MortgageMapBlock(MortgageChartBlock):

    class Meta:
        label = 'Mortgage Map Block'
        icon = 'image'
        template = '_includes/organisms/mortgage-map.html'

    class Media:
        js = ['mortgage-performance-trends.js']


class ResourceList(blocks.StructBlock):
    heading = blocks.CharBlock(required=False)
    body = blocks.RichTextBlock(required=False)
    has_top_rule_line = blocks.BooleanBlock(
        default=False,
        required=False,
        help_text='Check this to add a horizontal rule line above this block.'
    )
    image = atoms.ImageBasic(required=False)
    actions_column_width = blocks.ChoiceBlock(
        label='Width of "Actions" column',
        required=False,
        help_text='Choose the width in % that you wish to set '
                  'the Actions column in a resource list.',
        choices=[
            ('70', '70%'),
            ('66', '66%'),
            ('60', '60%'),
            ('50', '50%'),
            ('40', '40%'),
            ('33', '33%'),
            ('30', '30%'),
        ],
    )
    show_thumbnails = blocks.BooleanBlock(
        required=False,
        help_text='If selected, each resource in the list will include a '
                  '150px-wide image from the resource\'s thumbnail field.'
    )
    actions = blocks.ListBlock(blocks.StructBlock([
        ('link_label', blocks.CharBlock(
            help_text='E.g., "Download" or "Order free prints"'
        )),
        ('snippet_field', blocks.ChoiceBlock(
            choices=[
                ('related_file', 'Related file'),
                ('alternate_file', 'Alternate file'),
                ('link', 'Link'),
                ('alternate_link', 'Alternate link'),
            ],
            help_text='The field that the action link should point to'
        )),
    ]))
    tags = blocks.ListBlock(
        blocks.CharBlock(label='Tag'),
        help_text='Enter tag names to filter the snippets. For a snippet to '
                  'match and be output in the list, it must have been tagged '
                  'with all of the tag names listed here. The tag names '
                  'are case-insensitive.'
    )

    class Meta:
        label = 'Resource List'
        icon = 'table'
        template = '_includes/organisms/resource-list.html'


class AskCategoryCard(ModelList):

    def render(self, value, context=None):
        value['category'] = ask_cfpb.models.Category.objects.first()
        value.update(context or {})

        template = '_includes/organisms/ask-cfpb-card.html'
        return render_to_string(template, value)


class DataSnapshot(blocks.StructBlock):
    """ A basic Data Snapshot object. """
    # Market key corresponds to market short name for lookup
    market_key = blocks.CharBlock(
        max_length=20,
        required=True,
        help_text='Market identifier, e.g. AUT'
    )
    num_originations = blocks.CharBlock(
        max_length=20,
        help_text='Number of originations, e.g. 1.2 million'
    )
    value_originations = blocks.CharBlock(
        max_length=20,
        help_text='Total dollar value of originations, e.g. $3.4 billion'
    )
    year_over_year_change = blocks.CharBlock(
        max_length=20,
        help_text='Percentage change, e.g. 5.6% increase'
    )

    last_updated_projected_data = blocks.DateBlock(
        help_text='Month of latest entry in dataset'
    )
    # Market-specific descriptor text
    num_originations_text = blocks.CharBlock(
        max_length=100,
        help_text='Descriptive sentence, e.g. Auto loans originated'
    )
    value_originations_text = blocks.CharBlock(
        max_length=100,
        help_text='Descriptive sentence, e.g. Dollar volume of new loans'
    )
    year_over_year_change_text = blocks.CharBlock(
        max_length=100,
        help_text='Descriptive sentence, e.g. In year-over-year originations'
    )

    # Inquiry/Tightness Indices
    inquiry_month = blocks.DateBlock(
        required=False,
        max_length=20,
        help_text='Month of latest entry in dataset for inquiry data'
    )
    inquiry_year_over_year_change = blocks.CharBlock(
        required=False,
        max_length=20,
        help_text='Percentage change, e.g. 5.6% increase'
    )
    inquiry_year_over_year_change_text = blocks.CharBlock(
        required=False,
        max_length=100,
        help_text='Descriptive sentence, e.g. In year-over-year inquiries'
    )
    tightness_month = blocks.DateBlock(
        required=False,
        max_length=20,
        help_text='Month of latest entry in dataset for credit tightness data'
    )
    tightness_year_over_year_change = blocks.CharBlock(
        required=False,
        max_length=20,
        help_text='Percentage change, e.g. 5.6% increase'
    )
    tightness_year_over_year_change_text = blocks.CharBlock(
        required=False,
        max_length=100,
        help_text='Descriptive sentence, e.g. In year-over-year credit tightness'  # noqa
    )

    # Select an image
    image = images_blocks.ImageChooserBlock(required=False, icon='image')

    class Meta:
        icon = 'image'
        label = 'CCT Data Snapshot'
        template = '_includes/organisms/data_snapshot.html'
