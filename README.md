# Crypto Ticker

A library for displaying cryptocurrency and stock asset prices on an LED matrix panel using a Raspberry Pi.

Requires:

  * 64x32 LED Matrix Panel
  * Raspberry Pi Zero WH
  * Alpha Vantage API account

See the Howchoo guide for installation and configuration instructions:

https://howchoo.com/pi/raspberry-pi-cryptocurrency-ticker

## Settings

You can customize the application by adding any of the following settings to your settings.env file in the root directory of this repo:


| Name | Default | Description |
|--|--|--|
| SYMBOLS | btc,eth | The crypto symbols you want to track. |
| STOCKS | appl,tsla | The stock symbols you want to track. |
| REFRESH_RATE | 300 | How often to refresh price data, in seconds. |
| SLEEP | 3 | How long each asset price displays before rotating, in seconds. |
| AV\_API\_KEY | | The AlphaVantage API key, required if you selected stocks to track. |

Example:

```
SYMBOLS=btc,eth,ltc,xrp
STOCKS=appl,tsla
REFRESH_RATE=300
SLEEP=1
```
