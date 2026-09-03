"""Attrappen für Tests, die ohne laufende Anwendung auskommen."""


class FakeCombo:
    """Zustand einer ComboBox: aktuelle Auswahl und die auswählbaren Einträge."""

    def __init__(self, selected: str | None = None, options: tuple[str, ...] = ()) -> None:
        self.selected = selected
        self.options = list(options)


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
        return [
            FakeOption(self.combo, name)
            for name in self.combo.options
            if f"@Name='{name}'" in xpath
        ]


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
    """Attrappe des Treibers; windows: select übernimmt den Eintrag in die ComboBox."""

    def __init__(self) -> None:
        self.scripts: list[str] = []

    def execute_script(self, script: str, *args) -> None:
        self.scripts.append(script)
        if script == "windows: select":
            option = args[0]
            option.combo.selected = option.name
