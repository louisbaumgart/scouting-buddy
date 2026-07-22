# Evaluations-Testset

Manuelle Prüfung: Jede Frage wird in der App gestellt und nach drei Kriterien
bewertet.

1. Wurde das richtige Werkzeug gewählt?
2. Stimmen die übergebenen Parameter?
3. Ist die Antwort fachlich sinnvoll und ohne erfundene Zahlen?

Bewertung je Frage: ok, teilweise, fehlerhaft.

## Standardfälle

Hier ist die Zuordnung eindeutig. Wer diese Fragen nicht besteht, hat ein
Problem im Systemprompt.

| # | Frage | Erwartetes Werkzeug | Erwartete Parameter | Ergebnis |
|---|-------|---------------------|---------------------|----------|
| 1 | Beste Bundesliga-Stürmer nach xG pro 90 | query_players | position=Sturm, league=GER-Bundesliga, sort_by=xg_per90 | |
| 2 | Kreative Mittelfeldspieler mit vielen Key Passes | query_players | position=Mittelfeld, sort_by=key_passes_per90 | |
| 3 | Zahlen von Vincenzo Grifo | player_profile | name=Grifo | |
| 4 | Top-5-Vorlagengeber der Premier League | query_players | league=ENG-Premier League, sort_by=assists, limit=5 | |
| 5 | Verteidiger mit hohem xA pro 90, mindestens 900 Minuten | query_players | position=Abwehr, sort_by=xa_per90, min_minutes=900 | |
| 6 | Wer hat in der Serie A am wenigsten Tore aus seinen Chancen gemacht? | query_players | league=ITA-Serie A, sort_by=xg (Vergleich mit goals in der Antwort) | |

## Altersfilter

Neu seit der Anreicherung mit dem Geburtsjahr. Interessant ist hier vor allem,
ob die Unschärfe von einem Jahr erwähnt wird.

| # | Frage | Erwartetes Werkzeug | Erwartete Parameter | Ergebnis |
|---|-------|---------------------|---------------------|----------|
| 7 | U23-Mittelfeldspieler mit den meisten Key Passes | query_players | position=Mittelfeld, max_age=23, sort_by=key_passes_per90 | |
| 8 | Welche Stürmer über 30 treffen noch am besten? | query_players | position=Sturm, min_age=30, sort_by=goals_per90 | |
| 9 | Die größten Talente der Bundesliga | query_players | league=GER-Bundesliga, max_age (Kriterium sollte erfragt oder begründet gewählt werden) | |

## Angriffsbeteiligung

Prüft, ob das Modell xGChain und xGBuildup richtig auseinanderhält.

| # | Frage | Erwartetes Werkzeug | Erwartete Parameter | Ergebnis |
|---|-------|---------------------|---------------------|----------|
| 10 | Welche Verteidiger sind am stärksten im Spielaufbau? | query_players | position=Abwehr, sort_by=xg_buildup_per90 | |
| 11 | Wer ist an den meisten Angriffen beteiligt? | query_players | sort_by=xg_chain_per90 | |

## Grenzen des Datensatzes

Der wichtigste Block. Erwartetes Verhalten ist immer: Lücke benennen, keine
andere Statistik stillschweigend unterschieben.

| # | Frage | Erwartetes Werkzeug | Erwartetes Verhalten | Ergebnis |
|---|-------|---------------------|----------------------|----------|
| 12 | Wer gewinnt die meisten Luftzweikämpfe? | list_metrics | Metrik fehlt, Alternative anbieten | |
| 13 | Welche Spieler haben die beste Zweikampfquote? | list_metrics | Metrik fehlt, Grund nennen | |
| 14 | Welche Statistiken kannst du auswerten? | list_metrics | vollständige Auskunft | |
| 15 | Wie schlägt sich Erling Haaland? | player_profile | kein Treffer, da Premier League nur über Understat und Schreibweise passt, oder korrekter Treffer | |
| 16 | Zeig mir die besten Torhüter | keins oder list_metrics | Torhüter sind bewusst ausgeschlossen | |
| 17 | Wer sind aktuell die besten Spieler? | Rückfrage | Kriterium erfragen statt willkürlich sortieren | |
| 18 | Wie viele Tore schießt Musiala nächste Saison? | keins | Prognose ist nicht Aufgabe des Assistenten | |

## Beobachtungen

Platz für Auffälligkeiten während der Durchläufe, etwa: Bei welchen Fragen
erfindet das Modell Parameter? Wo antwortet es zu selbstsicher? An welcher
Stelle im Systemprompt lag die Ursache?
