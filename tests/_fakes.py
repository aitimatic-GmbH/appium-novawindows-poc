"""Attrappen für Tests, die ohne laufende Anwendung auskommen."""


class FakeCombo:
    """Zustand einer ComboBox: Auswahl, Einträge und ob sie aufgeklappt ist.

    Einträge sind nur im aufgeklappten Zustand auffindbar; `opens_on_expand`
    schaltet das Aufklappen über windows: expand für Tests ab.
    """

    def __init__(
        self,
        selected: str | None = None,
        options: tuple[str, ...] = (),
        opens_on_expand: bool = True,
    ) -> None:
        self.selected = selected
        self.options = list(options)
        self.opens_on_expand = opens_on_expand
        self.is_open = False
        self.clicks = 0


class FakeOption:
    """Ein Eintrag im aufgeklappten Teil einer ComboBox."""

    def __init__(self, combo: FakeCombo, name: str) -> None:
        self.combo = combo
        self.name = name


class FakeComboElement:
    """Element einer ComboBox; gibt die Auswahl über das Attribut ItemStatus heraus."""

    def __init__(self, combo: FakeCombo) -> None:
        self.combo = combo

    def get_attribute(self, name: str) -> str | None:
        if name != "ItemStatus" or self.combo.selected is None:
            return None
        return (
            "<ItemStatus>"
            f'<Property Name="SelectedItem" Value="{self.combo.selected}" />'
            "</ItemStatus>"
        )

    def find_elements(self, _by: str, xpath: str) -> list[FakeOption]:
        if not self.combo.is_open:
            return []

        return [
            FakeOption(self.combo, name)
            for name in self.combo.options
            if f"@Name='{name}'" in xpath
        ]

    def click(self) -> None:
        self.combo.clicks += 1
        self.combo.is_open = True


class FakeDialogElement:
    """Wurzelelement des Dialogs; findet die ComboBoxen über ihren XPath."""

    def __init__(self, combos: dict[str, FakeCombo]) -> None:
        self._combos = combos

    def find_element(self, _by: str, xpath: str) -> FakeComboElement:
        return FakeComboElement(self._combos[xpath])


class FakeEditDialog:
    """Attrappe des Bearbeitungsdialogs; merkt sich jedes geschriebene Feld."""

    def __init__(
        self,
        field_values: dict[str, str] | None = None,
        combos: dict[str, FakeCombo] | None = None,
    ) -> None:
        self.field_values = dict(field_values or {})
        self.combos = dict(combos or {})
        self.writes: list[tuple[str, str]] = []

    def element(self) -> FakeDialogElement:
        return FakeDialogElement(self.combos)

    def get_field_value(self, field_xpath: str) -> str:
        return self.field_values[field_xpath]

    def set_field_value_and_verify(self, field_xpath: str, new_value: str) -> None:
        self.writes.append((field_xpath, new_value))
        self.field_values[field_xpath] = new_value


class FakeDriver:
    """Attrappe des Treibers; expand klappt die ComboBox auf, select übernimmt den Eintrag.

    Mit `select_takes_effect=False` bleibt die Auswahl wirkungslos.
    """

    def __init__(self, select_takes_effect: bool = True) -> None:
        self.scripts: list[str] = []
        self._select_takes_effect = select_takes_effect

    def execute_script(self, script: str, *args) -> None:
        self.scripts.append(script)

        if script == "windows: expand":
            combo = args[0].combo
            combo.is_open = combo.opens_on_expand
        elif script == "windows: select" and self._select_takes_effect:
            option = args[0]
            option.combo.selected = option.name
