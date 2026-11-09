"""What a browser would send for a page's form, read from the page itself.

So a page test sends what the page really holds, with its hidden opening values, and a box
that is missing from the page cannot be sent by accident.
"""

from html.parser import HTMLParser


class FormReader(HTMLParser):
    """Reads one form's boxes. A template's rows are not on the page, and neither is what a
    disabled fieldset holds."""

    def __init__(self, form_id):
        super().__init__(convert_charrefs=True)
        self.form_id = form_id
        self.sent = {}
        self.inside = False
        self.in_template = 0
        self.disabled = False
        self.textarea = None
        self.select = None
        self.first_option = None
        self.chosen = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form" and attrs.get("id") == self.form_id:
            self.inside = True
        elif tag == "template":
            self.in_template += 1
        if not self.inside or self.in_template:
            return
        if tag == "fieldset" and "disabled" in attrs:
            self.disabled = True
        elif self.disabled:
            return
        elif tag == "input":
            self._read_input(attrs)
        elif tag == "textarea":
            self.textarea = attrs.get("name")
            self.sent[self.textarea] = ""
        elif tag == "select":
            self.select = attrs.get("name")
            self.first_option = None
            self.chosen = False
        elif tag == "option" and self.select:
            value = attrs.get("value", "")
            if self.first_option is None:
                self.first_option = value
            if "selected" in attrs:
                self.sent[self.select] = value
                self.chosen = True

    def _read_input(self, attrs):
        kind = attrs.get("type", "text")
        name = attrs.get("name")
        if not name or kind in ("submit", "button"):
            return
        if kind in ("radio", "checkbox") and "checked" not in attrs:
            return
        value = attrs.get("value", "")
        if name in self.sent:
            # A name the page holds more than once, like the answers already given, is sent
            # once for each, as a browser sends it.
            before = self.sent[name]
            self.sent[name] = [*before, value] if isinstance(before, list) else [before, value]
        else:
            self.sent[name] = value

    def handle_data(self, data):
        if self.textarea:
            self.sent[self.textarea] += data

    def handle_endtag(self, tag):
        if tag == "form":
            self.inside = False
        elif tag == "template":
            self.in_template -= 1
        elif tag == "textarea" and self.textarea:
            # A browser drops the newline right after the tag; this parser keeps it.
            self.sent[self.textarea] = self.sent[self.textarea].removeprefix("\n")
            self.textarea = None
        elif tag == "select" and self.select:
            if not self.chosen and self.first_option is not None:
                self.sent[self.select] = self.first_option
            self.select = None


def what_the_page_sends(html, **typed):
    """What the job card's form sends as it came, with these boxes typed over it."""
    reader = FormReader("job-form")
    reader.feed(html)
    return {**reader.sent, **typed}
