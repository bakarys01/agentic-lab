"""Contract checks for a bounded BDPM import."""

from datetime import date

import pytest

import scrapping.import_medications as medication_import
from scrapping.import_medications import parse_source_date, select_records


SPECIALTIES = "\n".join(
    [
        "60000001\tALPHA 10 mg, comprimé\tcomprimé\torale\tAutorisation active\tNationale\tCommercialisée\t01/01/2020\t\t\tTitulaire\tNon",
        "60000002\tBETA 20 mg, solution\tsolution\torale\tAutorisation active\tNationale\tCommercialisée\t01/01/2020\t\t\tTitulaire\tNon",
        "60000003\tGAMMA 30 mg, comprimé\tcomprimé\torale\tAutorisation active\tNationale\tCommercialisée\t01/01/2020\t\t\tTitulaire\tNon",
    ]
)
PRESENTATIONS = "\n".join(
    [
        "60000001\t1234567\tboîte de 10\tPrésentation active\tCommercialisée\t01/01/2020\t3400912345678\toui\t65%\t1,00\t1,00\t0,00\t",
        "60000001\t1234568\tboîte de 20\tPrésentation active\tCommercialisée\t01/01/2020\t3400912345685\toui\t65%\t2,00\t2,00\t0,00\t",
        "60000002\t1234569\tflacon\tPrésentation active\tCommercialisée\t01/01/2020\t3400912345692\toui\t65%\t3,00\t3,00\t0,00\t",
        "60000003\t1234570\tboîte\tPrésentation active\tCommercialisée\t01/01/2020\t3400912345708\toui\t65%\t4,00\t4,00\t0,00\t",
    ]
)
COMPOSITIONS = "\n".join(
    [
        "60000001\tcomprimé\t111\tSUBSTANCE A\t10 mg\tun comprimé\tSA\t1",
        "60000001\tcomprimé\t222\tSUBSTANCE B\t1 mg\tun comprimé\tSA\t2",
        "60000002\tsolution\t333\tSUBSTANCE C\t20 mg\t1 ml\tSA\t1",
        "60000003\tcomprimé\t444\tSUBSTANCE D\t30 mg\tun comprimé\tSA\t1",
    ]
)


def test_selection_keeps_every_child_for_selected_cis():
    selected = select_records(SPECIALTIES, PRESENTATIONS, COMPOSITIONS, limit=2)
    cis = {row[0] for row in selected.medications}

    assert len(cis) == 2
    assert {row[0] for row in selected.presentations} == cis
    assert {row[0] for row in selected.compositions} == cis
    assert len(selected.presentations) == sum(
        row.split("\t", 1)[0] in cis for row in PRESENTATIONS.splitlines()
    )
    assert len(selected.compositions) == sum(
        row.split("\t", 1)[0] in cis for row in COMPOSITIONS.splitlines()
    )
    assert select_records(SPECIALTIES, PRESENTATIONS, COMPOSITIONS, limit=2) == selected


def test_invalid_limit_and_missing_cis_fail_fast():
    with pytest.raises(ValueError, match="limit"):
        select_records(SPECIALTIES, PRESENTATIONS, COMPOSITIONS, limit=0)
    with pytest.raises(ValueError, match="available"):
        select_records(SPECIALTIES, PRESENTATIONS, COMPOSITIONS, limit=4)


def test_source_date_is_tied_to_the_correct_official_file():
    page = (
        '<a href="/download/file/CIS_bdpm.txt">Spécialités '
        '(Date de mise à jour : 29/09/2026)</a>'
        '<a href="/download/file/CIS_CIP_bdpm.txt">Présentations '
        '(Date de mise à jour : 07/10/2026)</a>'
    )
    assert parse_source_date(page, "CIS_bdpm.txt") == date(2026, 9, 29)
    assert parse_source_date(page, "CIS_CIP_bdpm.txt") == date(2026, 10, 7)
    with pytest.raises(ValueError, match="date"):
        parse_source_date(page, "CIS_COMPO_bdpm.txt")


def test_download_sources_decodes_each_file_with_its_own_encoding(monkeypatch):
    page = "".join(
        f'<a href="/download/file/{name}">Date de mise à jour : 07/10/2026</a>'
        for name in medication_import.FILES
    )
    payloads = {
        medication_import.SOURCE_PAGE: page.encode("utf-8"),
        medication_import.SOURCE_BASE + "CIS_bdpm.txt": "comprimé".encode("cp1252"),
        medication_import.SOURCE_BASE + "CIS_CIP_bdpm.txt": "boîte de comprimés".encode("utf-8"),
        medication_import.SOURCE_BASE + "CIS_COMPO_bdpm.txt": "LÉNALIDOMIDE".encode("cp1252"),
    }
    monkeypatch.setattr(medication_import, "_download", payloads.__getitem__)

    sources = medication_import.download_sources()

    assert sources["CIS_bdpm.txt"].text == "comprimé"
    assert sources["CIS_CIP_bdpm.txt"].text == "boîte de comprimés"
    assert sources["CIS_COMPO_bdpm.txt"].text == "LÉNALIDOMIDE"
