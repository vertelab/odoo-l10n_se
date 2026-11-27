Sveriges Riksbank as a currency rate provider for `currency_rate_update`.

Riksbank publishes one observation series per currency, `SEK<CUR>PMI`
(`SEKEURPMI`, `SEKUSDPMI`, ...), holding the value of one foreign unit in
SEK. This module replaces the SOAP based Linserv module
`currency_rate_live_riks_bank`, whose endpoint no longer answers.

The provider inverts every rate before it is stored: `res.currency.rate`
holds how many foreign units one SEK buys, Riksbank quotes the other way
round.

The Riksbank API allows about one request every five to ten seconds. The
provider waits eight seconds between the currency series and backs off when
Riksbank answers 429 Too Many Requests, up to three attempts per series.
