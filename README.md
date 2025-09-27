# aloitepalvelu
Ajamalla 

Tietokannat ja web-ohjelmointi kurssityö. Aloitepalvelussa voi tehdä aloitteita ja kerätä muiden käyttäjien digitaalisia-allekirjoituksia aloitteille.

Aloitepalvelussa voi tehdä aloitteita ja kerätä muiden käyttäjien digitaalisia-allekirjoituksia aloitteille.

1. Clone the repository
git clone https://github.com/livohka/aloitepalvelu.git
cd aloitepalvelu

2. Create and activate a virtual environment
python -m venv venv
# Windows
venv\Scripts\activate
# Linux / macOS
source venv/bin/activate

3. Install dependencies
pip install -r requirements.txt

4. Initialize the database with test data
python init.db.py

5. Run the development server
flask run --debug

6. Open in browser

Go to:
👉 http://127.0.0.1:5000

"admin", "admin123"
"matti", "salasana"




**Käyttäjän ominaisuudet.**<br>
Rekisteröityminen -valmis<br>
	Kirjautuminen - valmis<br>
  Käyttäjätilin hallinta ja poistaminen<br><br>

Digitaalinen allekirjoittaminen<br>
  Allekirjoitusten haku ja tarkastelu<br>
  Allekirjoittaminen<br>
  Allekirjoituksen päivittäminen<br>
  Allekirjoituksen poistaminen<br><br>



**Ylläpitäjän ominaisuudet**<br>
Aloitteen luominen - valmis<br>
  (alkupäivä, loppupäivä)<br>
  kuvauskentät ja kuvat tarvittaessa. -valmis<br>
  Aloitteen “muokkaus” -valmis<br>
  Aloitteen disabloitu -valmis<br>
  Aloitteen poisto, arkistonäkymä - valmis<br>
  Yhteenveto allekirjoituksista<br><br>

**Järjestelmänvalvojan ominaisuudet**<br>
Käyttäjätilien ja oikeuksien hallinta -valmis<br>
Aloitteiden ja allekirjoitusten hallinta -valmis<br><br>