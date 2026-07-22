# Evaluations-Testset

Für jede Frage wird geprüft: (1) richtiges Tool gewählt, (2) korrekte Parameter,
(3) fachlich sinnvolle Antwort. Ergebnis je Frage: ✅ / ⚠️ teilweise / ❌

| # | Frage | Erwartetes Tool | Erwartete Parameter | Ergebnis |
|---|-------|-----------------|---------------------|----------|
| 1 | Beste Bundesliga-Stürmer nach xG pro 90 | query_players | position=Sturm, league=GER-Bundesliga, sort_by=xg_per90 | |
| 2 | Kreative Mittelfeldspieler mit vielen Key Passes | query_players | position=Mittelfeld, sort_by=key_passes_per90 | |
| 3 | Zahlen von Vincenzo Grifo | player_profile | name=Grifo | |
| 4 | Top-5-Vorlagengeber der Premier League | query_players | league=ENG-Premier League, sort_by=assists, limit=5 | |
| 5 | Verteidiger mit hohem xA pro 90 (min. 900 Minuten) | query_players | position=Abwehr, sort_by=xa_per90, min_minutes=900 | |

… auf ~15 Fragen erweitern, inkl. schwieriger Fälle:
- Nicht abgedeckte Daten (z. B. Alter, Zweikampfquote – Spalten existieren nicht;
  erwartetes Verhalten: transparente Auskunft statt Halluzination)
- Mehrdeutige Fragen ("beste Spieler" – welches Kriterium?)
- Spieler, die nicht im Datensatz sind
