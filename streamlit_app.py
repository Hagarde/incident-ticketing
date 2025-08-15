import streamlit as st
import pandas as pd
from stix2 import Incident, Location, Relationship, Bundle
from pycti import OpenCTIApiClient
import uuid
import datetime
from datetime import datetime as dt

# --- Secrets depuis Streamlit Cloud ---
OPENCTI_API_URL = st.secrets["OPENCTI_URL"]
OPENCTI_API_TOKEN = st.secrets["OPENCTI_TOKEN"]
client = OpenCTIApiClient(OPENCTI_API_URL, OPENCTI_API_TOKEN)

# --- Charger les villes en cache ---
@st.cache_data
def load_villes():
    try:
        df = pd.read_csv("./019HexaSmal.csv", sep=";", encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv("./019HexaSmal.csv", sep=";", encoding="latin-1")

    return df

df_villes = load_villes()

# --- Formulaire ---
st.title("Création d'incident OpenCTI avec localisation")

titre = st.text_input("Titre (court)")
categorie = st.selectbox("Catégorie", ["Cyber", "Physique", "Organisationnel"])
description = st.text_area("Description (longue)")
interlocuteur = st.text_input("Interlocuteur")

# Recherche ville
search = st.text_input("Tapez le début de la ville ou un code postal")
ville_choisie = None

if len(search) >= 2:
    mask = (
        df_villes["Nom_de_la_commune"].str.contains(search, case=False, na=False)
        | df_villes["Code_postal"].astype(str).str.startswith(search)
    )
    results = df_villes[mask].sort_values("Nom_de_la_commune")

    if not results.empty:
        choix_ville = st.selectbox(
            "Choisissez une ville",
            results.apply(lambda row: f"{row['Nom_de_la_commune']} ({row['Code_postal']})", axis=1)
        )
        ville_choisie = results.iloc[
            list(results.apply(lambda row: f"{row['Nom_de_la_commune']} ({row['Code_postal']})", axis=1)).index(choix_ville)
        ]
    else:
        st.warning("Aucun résultat trouvé")
else:
    st.info("Tapez au moins 2 caractères pour rechercher une ville")

# --- Création bundle STIX ---
if st.button("Créer l'incident et la localisation"):
    try:
        # Incident
        incident_id = f"incident--{uuid.uuid4()}"
        incident = Incident(
            id=incident_id,
            name=titre,
            description=description,
            created=dt.now(datetime.timezone.utc),
            modified=dt.now(datetime.timezone.utc),
            labels=[categorie],
        )

        # Location
        location_id = f"location--{uuid.uuid4()}"
        location = Location(
            id=location_id,
            name=ville_choisie["Nom_de_la_commune"],
            description=f"Code postal : {ville_choisie['Code_postal']}",
            country="France"
        )

        # Relation
        relation_id = f"relationship--{uuid.uuid4()}"
        relation = Relationship(
            id=relation_id,
            relationship_type="located-at",
            source_ref=incident_id,
            target_ref=location_id,
            created=dt.now(datetime.timezone.utc),
            modified=dt.now(datetime.timezone.utc)
        )

        # Bundle
        bundle = Bundle(objects=[incident, location, relation])

        # Envoi vers OpenCTI
        result = client.stix2.import_bundle_from_json(bundle.serialize())

        st.success(f"Incident et localisation créés avec succès !")
        st.json(result)

    except Exception as e:
        st.error(f"Erreur : {e}")
