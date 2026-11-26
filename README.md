# AirPack Home – Home Assistant Integration

<

🇵🇱*(Polska wersja dokumentacji znajduje się poniżej)*🇵🇱

Integration for **Thesslagreen AirPack Home** heat recovery units (all h/v/f Energy/Energy+ models) via **Modbus RTU** (RS485 → USB).

## Key Features
- **Automatic USB Discovery:** The integration automatically detects your connected RS485 adapter.
- **Stable Connection:** Uses `/dev/serial/by-id/` paths automatically to ensure connectivity persists after reboots.
- **Full Control:** Supports Fan entity (speed 0-100%), operation modes (Auto/Manual/Boost), bypass control, and schedules.
- **Diagnostics:** Monitoring of all temperatures, airflow rates (CF), PWM voltages, and a full list of alarms.
- **Time Sync:** Automatically synchronizes the unit's clock with Home Assistant daily at 03:00.

## Requirements
- Home Assistant 2024.1.0+
- RS485 → USB adapter (e.g. CH340, FTDI, CP210x) **or** an RS485 ↔ Ethernet gateway (e.g. Waveshare RS485 TO ETH (B)) — see [Modbus TCP gateway](#modbus-tcp-gateway-rs485--ethernet)


## Installation via HACS
1. Open HACS → Integrations → **⋮ → Custom repositories**
2. Add your repository URL, Category: `Integration`
3. Search for **AirPack Home** and click Install
4. Restart Home Assistant

## Configuration
1. Settings → Devices & Services → **Add Integration** → search for "AirPack Home"
2. If an adapter is connected, it may be discovered automatically. Otherwise, select the port from the dropdown list.
3. Provide:
   - **Port**: Select from the list (recommended) or enter manually.
   - **Modbus Slave ID**: default is `10` (check unit label)
   - **Baudrate**: default is `9600`
     
## Schedule card

For the weekly ventilation schedule, install the companion
**[AirPack – Ventilation Schedule Card](https://github.com/arypien/airpack-schedule-card)**
(HACS, category: **Lovelace**).

It provides a per-day, per-episode editor for:

 - start time,
 - ventilation intensity (0–100%),
 - supply temperature,
 - ventilation start time.
 
It also provides:

 - a Winter / Summer switch,
 - a Restore defaults button,
 - a PL/EN localised interface.

The card uses the integration's time.*, number.*, and select.* entities and automatically discovers them based on the device prefix, so no manual configuration is required.

**Full documentation & screenshots:**  
👉 [github.com/arypien/airpack-schedule-card](https://github.com/arypien/airpack-schedule-card)


## Wiring / Connection
<img width="1024" height="935" alt="Gemini_Generated_Image_jawr94jawr94jawr" src="https://github.com/user-attachments/assets/84854d72-5b1c-4d5f-bea5-54d00eb4ae15" />
<img width="1920" height="1440" alt="reku" src="https://github.com/user-attachments/assets/326e586f-4bf8-4055-b61a-9fba84371fc7" />

### Quick setup
1. Connect the **A/B** data lines of the RS485 → USB adapter to the corresponding terminals on the unit.
2. If the adapter is not detected, swap A and B (reversed polarity).

## Modbus TCP gateway (RS485 ↔ Ethernet)

Instead of a USB adapter you can use an RS485↔Ethernet gateway (e.g. **Waveshare RS485 TO ETH (B)**).
The unit keeps speaking Modbus RTU; the gateway only bridges it to TCP.

1. Wire the gateway's **A/B** terminals to the unit's RS485 **A/B** (swap them if there is no answer).
2. Configure the gateway (web UI / Vircom):
   - **Baud rate 9600, 8N1** — same as the unit,
   - **Work mode**: either *Modbus TCP to RTU* (default) or *Transparent / TCP Server* — both are supported,
   - note the **TCP port** (typically `502`).
3. Settings → Devices & Services → **Add Integration** → **AirPack Home** → **Connection type: Ethernet — Modbus TCP gateway**.
4. Enter the gateway **IP**, **TCP port**, **Protocol mode = Auto-detect**, and the **Modbus device address** (default `10`).

Notes:
- With *Auto-detect* the integration probes both framings (Modbus TCP/MBAP and RTU-over-TCP) and keeps the one that answers, so no manual mode juggling is needed.
- Only one TCP connection should poll the unit: stop other Modbus masters pointed at the same gateway.
- HTTP access to the gateway web UI can stay enabled; it does not interfere with port 502.

### Checking the gateway before setup (optional)

`tests/tcp_gateway_probe.py` is a standalone read-only probe — it uses the same client code as the integration, so a green result means the integration will connect too:

```bash
pip install "pymodbus==3.13.1" pyserial
python tests/tcp_gateway_probe.py --host 192.168.1.254 --port 502
```

Sample output:

```
OK: connected to 192.168.1.254:502 in 0.12s
    framing in use : socket
    firmware       : 1.2.7
    filter type    : 4
    outside_temperature: 2.5
    ...
RESULT: 5/5 polls answered
```

`--framer socket` / `--framer rtu` force one mode; `--slave` and `--polls` adjust the device address and poll count.
---

# AirPack Home – Integracja Home Assistant 🇵🇱

Integracja dla rekuperatorów **Thesslagreen AirPack Home** (wszystkie modele h/v/f Energy/Energy+) przez protokół **Modbus RTU** (RS485 → USB).

## Główne cechy
- **Automatyczne wykrywanie USB:** Integracja sama wykrywa podłączony adapter RS485.
- **Stabilne połączenie:** Automatycznie używa ścieżek `/dev/serial/by-id/`, dzięki czemu nie stracisz połączenia po restarcie serwera.
- **Pełna kontrola:** Obsługa wentylatora (Fan), trybów pracy (Auto/Manual/Boost), bypassu i harmonogramów.
- **Diagnostyka:** Odczyt wszystkich temperatur, przepływów (CF), napięć PWM i pełna lista alarmów.
- **Synchronizacja czasu:** Automatycznie synchronizuje zegar rekuperatora z czasem HA codziennie o 03:00.

## Wymagania
- Home Assistant 2024.1.0+
- Adapter RS485 → USB (np. CH340, FTDI, CP210x) **lub** bramka RS485 ↔ Ethernet (np. Waveshare RS485 TO ETH (B)) — patrz [Bramka Modbus TCP](#bramka-modbus-tcp-rs485--ethernet) podłączony do serwera HA


## Instalacja przez HACS
1. Otwórz HACS → Integracje → **⋮ → Repozytoria niestandardowe**
2. Dodaj URL swojego repozytorium, typ: `Integration`
3. Wyszukaj **AirPack Home** i kliknij Zainstaluj
4. Uruchom ponownie Home Assistant

## Konfiguracja
1. Ustawienia → Urządzenia i usługi → **Dodaj integrację** → szukaj „AirPack Home"
2. Jeśli masz podłączony adapter, integracja może zostać wykryta automatycznie. Jeśli nie, wybierz port z listy rozwijanej.
3. Podaj:
   - **Port**: Wybierz z listy (zalecane) lub wpisz ręcznie.
   - **Adres Modbus**: domyślnie `10` (patrz etykieta urządzenia)
   - **Baudrate**: domyślnie `9600`
   - **GWC**: wybierz, czy instalacja posiada gruntowy wymiennik ciepła. Encje i odczyty GWC są dodawane tylko po włączeniu tej opcji.
  
## Karta harmonogramu

Do tygodniowego harmonogramu wentylacji zainstaluj dodatkową kartę
**[kartę AirPack – Ventilation Schedule](https://github.com/arypien/airpack-schedule-card)**
(HACS, kategoria: **Lovelace**).

Karta zapewnia edycję harmonogramu dla każdego dnia i każdego przedziału czasowego, w tym:

- godziny startu,
- intensywności wentylacji (0–100%),
- temperatury nawiewu,
- początku wietrzenia.

Dodatkowo dostępne są:

 - przełącznik Zima / Lato,
 - przycisk Przywróć domyślne,
 - interfejs w języku polskim i angielskim.

Wszystko działa w oparciu o encje time.*, number.* i select.* udostępniane przez tę integrację. Karta automatycznie wykrywa encje na podstawie prefiksu urządzenia, dzięki czemu nie wymaga ręcznej konfiguracji.

**Pełna dokumentacja i zrzuty ekranu:**  
👉 [github.com/arypien/airpack-schedule-card](https://github.com/arypien/airpack-schedule-card)

## Podłączenie

<img width="1024" height="932" alt="Gemini_Generated_Image_z8dy80z8dy80z8dy" src="https://github.com/user-attachments/assets/dfe317eb-fd4d-4277-ae13-fb60b3523e48" />
<img width="1920" height="1440" alt="reku" src="https://github.com/user-attachments/assets/3b0361cc-eba1-4b95-acc8-39a37c3616f5" />

### Szybkie podłączenie
1. Podłącz linie **A/B** adaptera RS485 → USB do odpowiednich zacisków urządzenia.
2. Gdy integracja nie wykrywa adaptera — zamień ze sobą A i B (odwrócona polaryzacja).

## Bramka Modbus TCP (RS485 ↔ Ethernet)

Zamiast adaptera USB można użyć bramki RS485↔Ethernet (np. **Waveshare RS485 TO ETH (B)**).
Rekuperator nadal mówi po Modbus RTU — bramka tylko przenosi ruch do TCP.

1. Podłącz zaciski **A/B** bramki do **A/B** RS485 rekuperatora (przy braku odpowiedzi zamień je miejscami).
2. Skonfiguruj bramkę (web UI / Vircom):
   - **Baudrate 9600, 8N1** — jak w rekuperatorze,
   - **Tryb pracy**: *Modbus TCP to RTU* (domyślny) albo *Transparent / TCP Server* — oba są obsługiwane,
   - zapisz **port TCP** (zwykle `502`).
3. Ustawienia → Urządzenia i usługi → **Dodaj integrację** → **AirPack Home** → **Typ połączenia: Ethernet — bramka Modbus TCP**.
4. Podaj **IP** bramki, **port TCP**, **Tryb protokołu = Auto-wykrywanie** oraz **adres Modbus urządzenia** (domyślnie `10`).

Uwagi:
- W trybie *Auto-wykrywanie* integracja sprawdza oba warianty ramkowania (Modbus TCP/MBAP oraz RTU-over-TCP) i zostaje przy tym, który odpowie — nie trzeba ręcznie zgadywać trybu bramki.
- Z bramką powinien rozmawiać tylko jeden klient Modbus (zatrzymaj inne magistrale/mastery wskazane na ten sam port).
- Web UI bramki może pozostać włączone — nie koliduje z portem 502.

### Szybki test bramki (opcjonalnie)

`tests/tcp_gateway_probe.py` to samodzielny test tylko-do-odczytu — używa tego samego klienta co integracja, więc zielony wynik oznacza, że integracja też się połączy:

```bash
pip install "pymodbus==3.13.1" pyserial
python tests/tcp_gateway_probe.py --host 192.168.1.254 --port 502
```

Parametry `--framer socket` / `--framer rtu` wymuszają jeden tryb, `--slave` i `--polls` zmieniają adres urządzenia i liczbę odpytań.

## Entities / Encje

### 🌍 GWC / Ground Heat Exchanger / Gruntowy Wymiennik Ciepła

If GWC is enabled during setup (or later in the integration options), the integration exposes the following GWC entities:

Jeśli GWC zostanie włączony podczas konfiguracji integracji (lub później w jej opcjach), integracja udostępnia następujące encje związane z GWC:

* **GWC status / Status GWC**
* **Regeneration type / Typ regeneracji**
* **GWC temperature / Temperatura GWC**

When GWC is disabled, no GWC-specific Modbus registers are read and no GWC entities are created.

Gdy GWC jest wyłączony, integracja nie odczytuje rejestrów Modbus związanych z GWC i nie tworzy żadnych encji GWC.

The integration also exposes the **summer and winter automatic schedules** as Home Assistant time entities: four time slots for each day of the week.

Integracja udostępnia również **automatyczne harmonogramy letnie i zimowe** jako encje typu `time` w Home Assistant: cztery przedziały czasowe dla każdego dnia tygodnia.

An unset schedule entry is reported as **unavailable**, because Home Assistant time entities cannot represent the AirPack disabled marker `0xA200`.

Niewprowadzony przedział czasowy jest oznaczany jako **niedostępny**, ponieważ encje typu `time` w Home Assistant nie mogą reprezentować znacznika wyłączenia AirPack `0xA200`.

### 🌬️ Fan / Wentylator

The main entity / Główna encja:

`fan.airpack_home`

It provides / Udostępnia:

* **On/Off / Włączanie i wyłączanie**
* **Speed 0–100% / Prędkość 0–100%**
* **Preset modes / Tryby pracy:**

  * **Auto / Automatyczny**
  * **Manual / Manualny**
  * **Boost / Wietrzenie**

### 🌡️ Temperatures / Temperatury

The integration exposes the following temperature and efficiency sensors:

Integracja udostępnia następujące sensory temperatury i sprawności:

* `outside_temperature` (TZ1) — **Outside temperature / Temperatura zewnętrzna**
* `supply_temperature` (TN1) — **Supply air temperature / Temperatura nawiewu**
* `exhaust_temperature` (TP) — **Exhaust air temperature / Temperatura wywiewu**
* `heat_recovery_efficiency` (%) — **Heat recovery efficiency / Sprawność odzysku ciepła**
* `fpx_temperature` (TZ2) — **FPX temperature / Temperatura FPX**
* `ambient_temperature` (TO) — **Ambient temperature / Temperatura otoczenia**

### 🚨 Alarms / Alarmy

All **S-type (blocking)** and **E-type (warning)** alarms are monitored as Home Assistant binary sensors.

Wszystkie alarmy typu **S (blokujące)** oraz **E (ostrzegawcze)** są monitorowane jako sensory binarne Home Assistant.

All alarm entities use the **Problem** device class.

Wszystkie encje alarmowe korzystają z klasy urządzenia **Problem**.


## License / Licencja
MIT

---

## Credits

This integration was developed with the assistance of **MIX AI**.  
The AI generated the code based on the official Modbus RTU register documentation  
provided by Thesslagreen. Testing, validation and real-world verification  
was performed by the repository author.

---

## Podziękowania 🇵🇱 ##

Integracja została napisana przy pomocy **MIX AI**.  
Kod powstał na podstawie oficjalnej dokumentacji rejestrów Modbus RTU  
dostarczonej przez Thesslagreen. Testowanie i weryfikacja na rzeczywistym  
urządzeniu zostały wykonane przez autora repozytorium.
