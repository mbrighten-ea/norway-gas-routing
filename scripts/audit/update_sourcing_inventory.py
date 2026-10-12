"""Reconcile the targeted sourcing evidence into the existing gap inventory."""
import hashlib
import json
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(ROOT / 'src'))
from norway_gas_routing.evaluation import read_parquet, EvaluationError
RAW = ROOT / 'data/raw/series_audit/sourcing_followup'
PATH = ROOT / 'evidence/inputs/model_input_gap_inventory.md'


def price_table(sids):
    lines = ['| SID | Unit; metadata lifecycle/frequency | Actual coverage; count | Value range; zeros; largest spacing | Assessment |',
             '|---|---|---|---|---|']
    for sid in sids:
        name = hashlib.sha256(sid.encode()).hexdigest()[:16]
        record = json.loads((RAW / (name + '.json')).read_text(encoding='utf-8'))
        meta = record['metadata']
        values = read_parquet(RAW / (name + '_MIN.parquet'))['value']
        periods = values.index.to_period('M')
        monthly = values.index.day.min() == values.index.day.max() == 1
        gaps = values.index.to_series().diff().max()
        notes = 'REVIEW: benchmark choice and aggregation not selected'
        if sid.startswith('teams'):
            notes = 'Monthly history + EA forecast; historical label/provenance not independently verified'
            if 'THE' in sid:
                notes += '; ends Dec 2026, forecast boundary absent, pre-Oct 2021 hub splice unresolved'
            else:
                notes += '; explicit forecast start Oct 2026; complete monthly horizon to Dec 2030'
            missing_months = len(pd.period_range(periods.min(), periods.max(), freq='M').difference(periods))
            assert monthly and missing_months == 0
        elif 'future_curve' in sid:
            notes = 'Monthly delivery grid despite daily metadata; lifecycle actual means market quote, not realised delivery; valuation date unverified'
        elif 'egix_day' in sid:
            notes = 'Business-day futures-based EGIX, not spot EGSI; ends Apr 2026; zeros require interpretation'
        else:
            notes = 'Day-ahead last trade, not daily index; irregular trading-date observations; gap/freshness and gas-day alignment unresolved'
        assert values.index.is_unique and not values.isna().any() and not (values < 0).any()
        first, last = str(values.index.min().date()), str(values.index.max().date())
        lines.append(f'| `{sid}` | {meta["unit"]}; {meta["lifecycle_stage"]}/{meta["frequency"]} | {first} to {last}; {len(values)} | {values.min():.3f} to {values.max():.3f}; {(values == 0).sum()} zeros; {gaps} | {notes} |')
    return '\n'.join(lines)


def main():
    raise EvaluationError('Historical inventory writer embeds reserved/future value findings. Retained evidence is immutable; use bounded build_series_audit for routine diagnostics.')
    model = yaml.safe_load((ROOT / 'config/model.yaml').read_text(encoding='utf-8'))
    active_availability = [asset['availability_series'] for asset in model['assets'].values()
                           if asset.get('active', True) and asset.get('availability_series')]
    assert len(active_availability) == 11
    assert all(asset['technical_capacity_mcm_d'] is None for asset in model['assets'].values())
    assert (ROOT / 'config/data_series.csv').read_bytes() in {
        (ROOT / 'data/raw/series_audit/registry_before_audit.csv').read_bytes(),
        (ROOT / 'evidence/inputs/data_series_proposed.csv').read_bytes()}
    text = PATH.read_text(encoding='utf-8')
    # Retain the original full requirement inventory; update only the sourcing gaps.
    text = text.replace('input gaps ? ', 'input gaps - ').replace('candidates ? researched', 'candidates - researched').replace('Sn?hvit', 'Snohvit')
    text = text.replace('No live SID calls, additional EA repositories', 'Targeted live SID discovery/samples permitted in this follow-up; no additional EA repositories')
    text = text.replace('None of the inspected local evidence supplies a defensible numeric technical/nameplate baseline for an active coded asset.', 'Public candidates below now establish published technical/transport facts; none is an approved model maintenance reference or configured baseline.')
    text = text.replace('Local catalogue identifiers for Emden firm technical rights exist, but have only series_id metadata, no retained values/unit/frequency/lifecycle.', 'The four Emden firm technical identifiers below now have retained metadata and three eight-day samples (January 2025, September 2026, December 2030).')
    price_heading = '## Retrieved wholesale price candidates' if '## Retrieved wholesale price candidates' in text else '## Price SID candidates from local metadata'
    start = text.index(price_heading)
    end = text.index('## Derived targets and controls', start)
    prices = ['teams\\natural_gas\\price\\' + hub for hub in ['nbp', 'ttf', 'THE', 'ZTP', 'peg']]
    prices += [r'teams\natural_gas\price\NBP_EUR_MWh', r'teams\natural_gas\price\TTF_forecaster']
    prices += [rf'eex2\future\month\{hub}\settlement_price\future_curve' for hub in ['nbp', 'ttf', 'the', 'ztp', 'peg', 'etf']]
    prices += [rf'eex2\indices\egix_day\{hub}' for hub in ['nbp', 'ttf', 'the', 'ztp', 'peg', 'etf']]
    prices += [rf'eex2\spot\day_ahead\{hub}\last_price' for hub in ['ttf', 'the', 'ztp', 'peg', 'etf']]
    price_section = '''## Retrieved wholesale price candidates - 8 October 2026

These are sourcing candidates, not approved commercial inputs. Exact SIDs, metadata and returned observations are retained under data/raw/series_audit/sourcing_followup. EA monthly NBP/TTF/ZTP/PEG series include history and forecast; a forecast lifecycle does not turn earlier values into an independent validation target. All five primary monthly price candidates report source workbooks; THE points to a different workbook, has no forecast-start metadata and stops at December 2026. Its pre-October 2021 history cannot be called historical THE without resolving the predecessor splice. NBP_EUR_MWh avoids a new analyst-invented FX/therm conversion; the existing converted series is a candidate whose source conversion remains unverified.

Denmark: ETF is an actual Danish hub candidate, not a selected TTF/THE proxy. EEX ETF metadata lacks country_iso, explaining its absence from country-filtered discovery. No long-term EA Danish forecast was identified in the targeted EA price container. The ETF forward curve stops in November 2026. Selection of ETF versus another approved Danish benchmark remains an analyst choice.

Public definitions: [EEX indices](https://www.eex.com/en/markets/natural-gas/gas-market-transparency) distinguishes futures-based Daily EGIX, delivery-period EGSI, within-day and front-month settlement indices. [EEX spot products](https://www.eex.com/en/markets/natural-gas/gas-spot) identifies day-ahead contracts. [EEX January 2026 volumes](https://www.eex-group.com/fileadmin/SAP_Marketing_Cloud_E-Mail_Attachments/communications_and_marketing/Press_Releases/20260204_EEX_Group_January_2026_Volumes_table.pdf) explicitly identifies Danish ETF. [EEX German merger notice](https://www.eex.com/en/newsroom/detail?cHash=5aca64ffd331779039946fc1b1abab29&tx_news_pi1%5Baction%5D=detail&tx_news_pi1%5Bcontroller%5D=News&tx_news_pi1%5Bnews%5D=3149) dates THE market merger to 1 October 2021. Accessed 8 October 2026; no public prices substituted for EA data.

All retrieved price series have no explicit nulls, duplicates or negative observations. Missing calendar/trading periods are distinct from explicit nulls. Most EEX histories stop in April/May 2026; PEG last-trade history stops in October 2024. Noon naive timestamps do not establish gas-day assignment. Curve observations are monthly delivery dates, not a history of daily valuation dates: latest valuation/as-of freshness cannot be inferred from long delivery coverage or lifecycle=actual. No spot/futures/EA forecast blend or monthly price averaging has been chosen.

'''+price_table(prices)+'\n\n'
    text = text[:start] + price_section + text[end:]
    assessment = {
        'nyhamna': 'Conditionally redundant raw availability SID: audited daily NO_maintenance_Nyhamna can provide signed derate; confirm reference baseline and plant-only scope before mapping.',
        'karsto': 'Conditionally redundant raw availability SID: audited daily NO_maintenance_Karsto exists; rich/dry reference and shared plant scope remain unresolved.',
        'nybro_exit': 'Conditionally redundant raw availability SID: daily NO_maintenance_Nybro exists; establish North Sea Entry rather than combined Nybro scope and reference conditions first.',
        'ogt': 'Genuine missing corridor outage evidence. Oseberg/Heimdal field or site maintenance is validation-only; not established as OGT pipe derate.',
        'europipe_i': 'Genuine missing corridor outage evidence. Emden/Dornum terminal maintenance does not identify this pipeline separately.',
        'europipe_ii': 'Genuine missing shared-corridor outage evidence. Dornum site maintenance does not separately measure the upstream corridor or Danish branch.',
        'norpipe': 'Genuine missing corridor outage evidence. Emden terminal/Ekofisk field maintenance is validation-only, not a proven Norpipe derate.',
        'langeled_south': 'Easington daily maintenance is validation-only landing evidence; full southern-pipeline scope/reference not established. Route availability remains REVIEW.',
        'vesterled': 'St_Fergus daily maintenance is validation-only terminal evidence; do not combine SEGAL or infer full Vesterled pipe outage. Route availability remains REVIEW.',
        'zeepipe_export': 'Zeebrugge daily maintenance is validation-only receiving-terminal evidence; export pipe outage/reference not established. Route availability remains REVIEW.',
        'franpipe': 'Dunkerque daily maintenance is validation-only terminal evidence; full Franpipe pipe outage/reference not established. Route availability remains REVIEW.'}
    lines = text.splitlines()
    for i, line in enumerate(lines):
        for name, note in assessment.items():
            if line.startswith('| availability_' + name + ' | Active asset'):
                parts = line.split('|')
                parts[-2] = ' ' + note + ' Code currently ingests maintenance only for Kollsnes; no mapping changed. '
                lines[i] = '|'.join(parts)
        if line.startswith('| price_') and 'Six-market price definition' in line:
            parts = line.split('|')
            parts[-2] = ' Candidates retrieved below; canonical SID remains blank. THE/Denmark long-term forecast and benchmark/valuation choices remain unresolved. '
            lines[i] = '|'.join(parts)
    text = '\n'.join(lines) + '\n'
    if '## Availability versus existing maintenance:' in text:
        start = text.index('## Availability versus existing maintenance:')
        end = text.index('## Public capacity candidates', start)
        text = text[:start] + text[end:]
    insert = text.index('## Public capacity candidates')
    availability = '''## Availability versus existing maintenance: all 11 active requirements

There is no requirement for an independent raw availability SID if a matching daily signed maintenance derate and approved reference already determine the same constraint. For Nyhamna, Karsto and Nybro, an additional availability representation is conditionally redundant; it is not another subtraction or independent validation target. Eight corridor requirements remain unresolved: four have no matching corridor evidence (OGT, Europipe I, Europipe II, Norpipe); four have landing-terminal maintenance leads only (Langeled South, Vesterled, Zeepipe export, Franpipe). Landing-series use could avoid another SID only after the full-route scope is established; terminal and pipe derates must not be added blindly.

All relevant retained daily maintenance series span 2021-01-01 to 2030-12-31 in mcm_d with audited daily spacing; they are reference-only except approved Kollsnes. Prefix: `teams\\natural_gas\\EUR\\daily_NO\\NO_maintenance_`. Exact suffixes: Nyhamna, Karsto, Nybro, Easington, St_Fergus, Zeebrugge, Dunkerque, Emden, Dornum, Oseberg, Heimdal, Sleipner. Scope in the retained description is the named site only. Oseberg/Heimdal/Sleipner and all upstream/field maintenance remain QA/reference, avoiding double counting exogenous production outages. Pre-opening zero Nybro adjustments do not prove physical availability before 2022. Existing signed negative diagnostics and available = reference - maintenance remain unchanged.

Registry-only Langeled North, Zeepipe IIA/IIB, Statpipe core and Dornum receiving availability, plus inactive Emden receiving availability, are not current coded input requirements. This does not establish that those physical facilities never constrain the real network.

### Capacity-to-arc scope checks

- OGT's physical Oseberg-to-Heimdal-bypass segment precedes both the Vesterled and Statpipe/core branches. Coded OGT constrains OSEBERG_CORE only; UK bypasses it. The 35.0 candidate therefore does not establish correct shared enforcement without a modeller decision.
- Karsto processing is upstream of both Statpipe/core and Europipe II. Coded KARSTO_INJECTION constrains KARSTO_CORE only; KARSTO_EUROPIPE_II bypasses it. Do not silently apply a plant number to the core branch or introduce a shared constraint.
- Europipe II is correctly represented as one upstream asset before Germany/Denmark split. Its 73.5 cannot be granted independently to both destinations. North Sea Entry is an additional branch constraint, not a second independent supply.
- Other corridor endpoints match the collapsed CORE/landing arcs, subject to the model's existing collapse. Norpipe originates at Ekofisk rather than CORE; Zeepipe's 42.2 is the export leg, not internal 55.0; Langeled South's 73.8 is not North's 74.7. Do not import internal transfer capacities as extra constraints during sourcing.
- Eight Gassco values are explicit MSm3/d transport capacities as of 2024, not available/booked or observed maxima. Exact change dates, hydraulic conditions and validity through 2030 are not documented by the map; retain REVIEW for configuration application.
- Nyhamna's 84 plant export capacity and 2024 Langeled North 74.7 are different asset/reference facts. Do not select a minimum or overwrite the existing injection definition during this pass.

### Emden GTS small-sample results

All four candidates retrieve successfully: unit kWh_d (source kWh/d), metadata actual/daily, one observation per day in each of three inclusive eight-day windows. EPT1 entry is 963,600,000 kWh/day in January 2025 and September 2026, and 878,400,000 in December 2030. EPT1 exit, NPT entry and NPT exit are zero in all sampled windows. Zero technical capacity in these samples is not proof of permanent absence of a physical connection. Source point keys are ITP-00160/EPT1 and ITP-00161/NPT; directions are from GTS's perspective. Generic economic_property=exports is misleading for entry: source_obj.directionkey is the relevant direction.

EPT1 entry is relevant to the Dutch allocation branch and is distinct from Norwegian corridor/Emden receiving nameplate; the current Dutch arc has no capacity asset. EPT1 exit is reverse direction. No automatic sum of NPT/EPT1, no conversion to mcm/d without matching calorific/reference conditions, and no new Dutch branch constraint. Firm Technical is the maximum firm transport product, distinct from Firm Available and Firm Booked; neither scope nor guaranteed future availability follows from its distant dates. Samples retained under sourcing_followup; full capacity history was not audited.

'''
    text = text[:insert] + availability + text[insert:]
    text = text.replace('11 active availability SIDs/semantics are missing, 12 active infrastructure baselines are unsourced', 'three new availability representations are conditionally redundant and eight corridor outage scopes remain unresolved; published capacity candidates are evidenced but unapproved')
    text = text.replace('six wholesale price histories/forward or forecast inputs, long-dated coverage to December 2030', 'price candidates below are retrieved; THE EA forecast ends in 2026 and no long-dated Danish forecast was identified; benchmark choice and valuation-date freshness')
    text = text.replace('No live SID observations were retrieved.', 'Targeted new Emden samples and price observations were retrieved via the existing helper; no maintenance/production audit was repeated.')
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith('| NYHAMNA_INJECTION | 84'):
            lines[i] = '| NYHAMNA_INJECTION | 84 million Sm3/day | Plant export capacity after expansion | Gassco report 1 Oct 2017 says already 84; corroborated current page, accessed 8 Oct 2026; exact upgrade day not supplied | REVIEW: strong plant candidate, maintenance reference/time history not approved; distinct from Langeled North 74.7 |'
        elif line.startswith('| KARSTO_INJECTION | Around'):
            lines[i] = '| KARSTO_INJECTION | Around 95 million Sm3 rich gas/day; Equinor current prose says around 98 million Sm3 without denominator | Official Norskpetroleum explicitly verifies daily rich-gas processing; not dry-gas export | Undated current official page accessed 8 Oct 2026; Equinor expansion report 29 Sep 2005 establishes historical 88 million Sm3/day | REVIEW: current 95 versus 98 not resolved; rich/dry boundary and reference baseline unapproved |'
        elif line.startswith('| NYBRO_EXIT | Up'):
            lines[i] = '| NYBRO_EXIT | 27.4 mcm/day in technical N-1 tables; 27 rounded in prose; annual 10,387 mcm differs | North Sea Entry Norwegian branch, part of combined Nybro entry; not Denmark-only consumption | Danish Energy Agency plan dated 28 Feb 2025 covers 2023-2027; full commissioning 1 Dec 2022; Energinet 2020 expected 13,400 MWh/hour from Oct 2022 | REVIEW: technical definition now explicit; normal/standard conditions, numerical reference differences and transit scope remain unresolved |'
        elif line.startswith('| KOLLSNES_INJECTION | 156'):
            lines[i] = line.replace('older 143 text stale/conflicting', '143 site text conflicts; official Norskpetroleum distinguishes older 146.5 rich-gas processing from 143 dry-gas export; 156 processing cannot automatically be equated to dry-gas injection')
        elif line.startswith('| EMDEN_RECEIVING | None identified'):
            lines[i] = line.replace('No retained observations or unit metadata', 'Daily kWh/d samples now retained; directions and product distinct from receiving plant')
        if line.startswith('| ') and 'Missing technical baseline; dynamic SID missing.' in line:
            lines[i] = lines[i].replace('Missing technical baseline; dynamic SID missing.', 'Published candidate remains unapproved; dynamic scope assessed below.')
    text = '\n'.join(lines) + '\n'
    source_marker = 'No maintenance reference was equated automatically'
    source_note = '''New targeted primary evidence (all accessed 8 October 2026):

- [Gassco Nyhamna, 1 October 2017](https://gassco.eu/nyhamna-styrker-norges-posisjon-som-gasseksportor/) establishes 84 million Sm3/day export capacity already after expansion, rather than an undated first assertion.
- [Official Norskpetroleum land facilities](https://www.norskpetroleum.no/produksjon-og-eksport/landanlegg/) establishes around 95 million Sm3/day rich-gas Karsto processing; distinguishes older Kollsnes rich feed 146.5 from dry export 143. [Equinor Karsto expansion, 29 September 2005](https://www.equinor.com/news/archive/2005/09/29/KrstExpansionOnTimeAndUnderBudget) establishes historical 88 million Sm3/day. Neither historical 88 nor current 95/98 is an approved dry-gas reference for this model. [2018 Gassco brochure](https://gassco.eu/wp-content/uploads/2023/04/Karsto-brosjyren-engelsk-final-1218-1.pdf) separates rich input, dry output and liquid products; outlet pipeline capacities are not a plant nameplate inferred by summation.
- [Danish Energy Agency Preventive Action Plan, 28 February 2025](https://ens.dk/media/5370/download), pp.9 and 25-27, explicitly labels North Sea Entry technical capacity 27.4 mcm/day, rounds to 27 in prose and lists 10,387 mcm/year (not arithmetically identical to 27.4 x 365). Annual-table volumes use 12.1 kWh/Nm3; this document-specific factor is not approved for EPT1 or other gas. [Energinet branch methodology](https://en.energinet.dk/media/ycuhglla/methodology-for-integrating-baltic-pipe-in-the-danish-market-model.pdf), p.15, distinguishes expected technical 13,400 MWh/hour, sold 10,600 and available 2,800 for North Sea Entry from October 2022. These are different quantities, not interchangeable capacities.
- [GTS cross-border capacity appendix](https://www.gasunietransportservices.nl/uploads/fckconnector/ba836e79-1c54-5d75-b40e-33b76da2ac38) independently lists Emden EPT entry 40.2 (unit/date must be read in context before comparison). [GTS interdependence definition](https://www.gasunietransportservices.nl/begrippenlijst/onderlinge-afhankelijkheid) explicitly states Emden EPT/NPT free capacities are interdependent; no independent capacity sum is defensible. [ENTSOG April 2026 outlook](https://www.entsog.eu/sites/default/files/2026-04/SO0069-26_Summer%20Supply%20Outlook%202026.pdf), p.11, defines technical capacity as the maximum firm offer subject to integrity/operational requirements; it is not a historical maximum or automatically an unchanging engineering nameplate.

'''
    if 'New targeted primary evidence (' not in text:
        text = text.replace(source_marker, source_note + source_marker)
    text = text.replace('independently lists Emden EPT entry 40.2 (unit/date must be read in context before comparison)', 'draft dated 1 November 2021, Appendix VI p.124, lists Emden EPT entry 40.2 GW for October 2021-2027. The SID sample 963.6 million kWh/day equals 40.15 GW, consistent with that rounded energy capacity; sampled December 2030 equals 36.6 GW and is lower than the older draft projection')
    text = text.replace('price candidates below are retrieved;', 'price candidates above are retrieved;')
    text = text.replace('EPT1 entry is relevant to the Dutch allocation branch', 'GTS explicitly identifies interdependence of free capacity at Emden EPT/NPT; do not sum them. EPT1 entry is relevant to the Dutch allocation branch')
    PATH.write_text(text, encoding='utf-8')
    # The aborted free-text query returned unrelated hits. Retain the query/count,
    # not a large unrelated catalogue, and never repeat this syntax in retrieval.
    path = RAW / ('query_' + hashlib.sha256(b'NBP').hexdigest()[:16] + '.json')
    if path.exists():
        record = json.loads(path.read_text(encoding='utf-8'))
        if 'sids' in record:
            record['unrelated_hit_count'] = len(record.pop('sids'))
            record['excluded_reason'] = 'Bare free-text syntax was not hub-specific; replaced by structured metadata/prefix queries.'
            path.write_text(json.dumps(record, indent=2), encoding='utf-8')
    print('Updated existing inventory; checked 24 price series and all 11 availability requirements.')


if __name__ == '__main__':
    main()
