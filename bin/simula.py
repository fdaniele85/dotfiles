#!/usr/bin/env python3

import argparse
import datetime
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def endpoint_from_environment():
    endpoint = os.getenv("SWRR_API_URL", "http://localhost:3000").strip().rstrip("/")
    if not endpoint.startswith(("http://", "https://")):
        endpoint = f"http://{endpoint}"
    return endpoint


API_ENDPOINT = endpoint_from_environment()


def api_request(path, payload=None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        f"{API_ENDPOINT}{path}",
        data=body,
        headers=headers,
        method="POST" if body is not None else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        response_body = error.read().decode("utf-8")
        try:
            message = json.loads(response_body).get("error", response_body)
        except json.JSONDecodeError:
            message = response_body
        raise RuntimeError(f"Errore API {error.code}: {message}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Impossibile raggiungere {API_ENDPOINT}: {error.reason}") from error


def flatten_tables(tables):
    flattened = []

    def visit(table, path=""):
        label = f"{path} › {table['label']}" if path else table["label"]
        flattened.append({
            "key": table["key"],
            "label": label,
            "section": table["section"],
        })
        for item in table.get("items", []):
            child = item.get("childTable")
            if child:
                visit(child, label)

    for table in tables:
        visit(table)
    return flattened


def get_tables():
    return flatten_tables(api_request("/api/tables").get("tables", []))


def resolve_table(identifier, tables):
    exact_key = next((table for table in tables if table["key"] == identifier), None)
    if exact_key:
        return exact_key

    matches = [table for table in tables if table["label"].casefold() == identifier.casefold()]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        keys = ", ".join(table["key"] for table in matches)
        raise RuntimeError(f"Nome tabella ambiguo; usa una di queste chiavi: {keys}")
    raise RuntimeError(f"Tabella '{identifier}' non trovata; usa --list-tables per vedere quelle disponibili")


def print_tables(tables):
    section_names = {
        "contenuti": "In lettura / Serie",
        "generi": "Generi",
    }
    for section in ("contenuti", "generi"):
        section_tables = [table for table in tables if table["section"] == section]
        if not section_tables:
            continue
        print(f"\n{section_names[section]}:")
        for table in section_tables:
            print(f"  {table['key']:<44} {table['label']}")


def print_simulation(result, pause=False):
    for entry in result["timeline"]:
        mode = "Settimanale" if entry.get("scheduleMode") == "weekly" else f"Quota: {entry['quota']}"
        print(
            f"Sessione {entry['session']:3d} [{format_datetime(entry.get('simulatedAt'))}]: "
            f"{entry['name']} ({mode})"
        )

    if pause:
        input("\nPremi INVIO per vedere il riepilogo finale...")

    print(f"\n=== RISULTATO SIMULAZIONE IN {result['sessions']} SESSIONI ===")
    print(f"Tabella: {result['table']['label']}")
    print(f"Inizio: {format_datetime(result.get('startedAt'))}")
    print(f"Quota totale gruppo: {result['totalQuota']}\n")

    for item in result["results"]:
        weekly = item.get("scheduleMode") == "weekly" or item.get("expectedPercentage") is None
        mode = "Settimanale" if weekly else f"Quota: {item['quota']:<4}"
        theoretical = "   —  " if weekly else f"{item['expectedPercentage']:5.1f}%"
        print(
            f"{item['consumptions']:3d} sessioni | {item['name']:<35} "
            f"({mode:<12} | "
            f"Reale: {item['actualPercentage']:5.1f}% | "
            f"Teorica: {theoretical})"
        )


def format_datetime(value):
    if not value:
        return "—"
    try:
        parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone().strftime("%d/%m/%Y %H:%M")
    except (TypeError, ValueError):
        return str(value)


def parse_arguments():
    parser = argparse.ArgumentParser(description="Simulatore SWRR via API SWRR Media Tracker")
    parser.add_argument(
        "--table",
        "--database",
        dest="table",
        help="Chiave o nome della tabella (--database è mantenuto per compatibilità)",
    )
    parser.add_argument("--target", type=int, help="Ferma quando un elemento raggiunge N consumi")
    parser.add_argument("--all", type=int, help="Ferma quando tutti gli elementi raggiungono almeno N consumi")
    parser.add_argument("--days", type=int, help="Numero di sessioni da simulare")
    parser.add_argument(
        "--start",
        help="Data e ora iniziale in formato ISO 8601 (default: momento della chiamata API)",
    )
    parser.add_argument("--pause", action="store_true", help="Pausa prima del riepilogo finale")
    parser.add_argument("--debug", action="store_true", help="Stampa la risposta JSON completa")
    parser.add_argument("--list-tables", action="store_true", help="Elenca le tabelle disponibili e termina")
    return parser.parse_args()


def main():
    args = parse_arguments()
    criteria = {
        key: value
        for key, value in (("days", args.days), ("target", args.target), ("all", args.all))
        if value is not None
    }

    if any(value < 1 for value in criteria.values()):
        print("Errore: days, target e all devono essere interi maggiori di zero", file=sys.stderr)
        return 2

    try:
        tables = get_tables()
        if args.list_tables:
            print_tables(tables)
            return 0
        if not args.table:
            print("Errore: specifica --table oppure usa --list-tables", file=sys.stderr)
            return 2
        if not criteria:
            print("Errore: specifica almeno uno tra --target, --days o --all", file=sys.stderr)
            return 2

        table = resolve_table(args.table, tables)
        table_key = urllib.parse.quote(table["key"], safe="")
        if args.start:
            criteria["startedAt"] = args.start
        result = api_request(f"/api/tables/{table_key}/simulate", criteria)
    except RuntimeError as error:
        print(f"Errore: {error}", file=sys.stderr)
        return 1

    if args.debug:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    print_simulation(result, pause=args.pause)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
