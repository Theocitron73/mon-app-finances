import streamlit as st
import pandas as pd
import io
import plotly.express as px
import os
import re
import time
import plotly.graph_objects as go
from streamlit_option_menu import option_menu

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Mes Budgets", layout="wide",initial_sidebar_state="collapsed")


st.markdown("""
<style>
    /* 1. ADAPTATION GLOBALE MOBILE */
    @media (max-width: 768px) {
        /* On réduit les marges énormes du container Streamlit */
        [data-testid="stAppViewBlockContainer"] {
            padding: 1rem 0.5rem !important;
        }

        /* On force les colonnes à s'empiler verticalement */
        [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            margin-bottom: 10px;
        }

        /* On réduit la taille des titres pour mobile */
        h1 { font-size: 1.5rem !important; }
        h2 { font-size: 1.2rem !important; }
        h3 { font-size: 1.1rem !important; }

        /* Ajustement des métriques (tes KPI en haut) */
        [data-testid="stMetricValue"] {
            font-size: 1.2rem !important;
        }
    }

    /* 2. OPTIMISATION DU MENU (streamlit-option-menu) */
    /* Pour éviter que le menu horizontal ne déborde */
    .nav-link {
        padding: 5px !important;
        font-size: 12px !important;
        white-space: nowrap;
    }

    /* 3. TES COMPOSANTS PERSONNALISÉS (Lignes 1125+) */
    /* On remplace les largeurs fixes par du 100% */
    .votre-classe-conteneur-groupe {
        width: 100% !important;
        max-width: 100% !important;
        overflow-x: auto; /* Permet de scroller le tableau si trop large */
    }

    /* Correction pour ton gradient de fond pour qu'il couvre tout */
    .stApp {
        background-attachment: fixed;
    }
</style>
""", unsafe_allow_html=True)


st.markdown("""
<style>
    /* 1. Supprimer l'espace vide tout en haut de la page */
    .block-container {
        padding-top: 0rem !important;
        padding-bottom: 0rem !important;
        margin-top: -30px !important; /* Remonte le contenu vers le haut */
    }

    /* 2. Masquer la barre d'outils Streamlit si nécessaire pour gagner de la place */
    [data-testid="stHeader"] {
        background: transparent !important;
        height: 0px !important;
    }

    /* 3. S'assurer que le conteneur du menu n'est pas bridé en hauteur */
    div[data-testid="stCustomComponentV1"] {
        overflow: visible !important;
        height: auto !important;
        min-height: 100px !important; /* Ajuste selon la taille de tes carrés */
    }
</style>
""", unsafe_allow_html=True)



def update_couleur_compte(nom_compte):
    # 1. On identifie le widget qui vient d'être cliqué
    cle_picker_actuel = f"cp_{nom_compte}"
    
    if cle_picker_actuel in st.session_state:
        # 2. On met à jour le dictionnaire config_groupes avec TOUTES les couleurs
        # présentes dans le session_state (pour éviter le retour au bleu des autres)
        for c in st.session_state.config_groupes:
            cle_p = f"cp_{c}"
            if cle_p in st.session_state:
                # On prend la couleur en direct du widget
                st.session_state.config_groupes[c]["Couleur"] = st.session_state[cle_p]
            elif "Couleur" not in st.session_state.config_groupes[c]:
                # Sécurité si le widget n'existe pas encore
                st.session_state.config_groupes[c]["Couleur"] = "#1f77b4"

        # 3. On sauvegarde le dictionnaire complet qui est maintenant à jour
        sauvegarder_config(st.session_state.config_groupes)

# --- 2. SESSION STATE (La mémoire) ---
if 'df' not in st.session_state:
    # --- CHARGEMENT AUTO AU DÉMARRAGE ---
    if os.path.exists("ma_base_de_donnees.csv"):
        try:
            df_load = pd.read_csv("ma_base_de_donnees.csv", encoding='utf-8-sig')
            df_load["Date"] = pd.to_datetime(df_load["Date"], errors='coerce')
            st.session_state.df = df_load
        except:
            st.session_state.df = pd.DataFrame(columns=["Date", "Nom", "Montant", "Categorie", "Compte", "Mois"])
    else:
        st.session_state.df = pd.DataFrame(columns=["Date", "Nom", "Montant", "Categorie", "Compte", "Mois"])

if 'choix_g' not in st.session_state:
    st.session_state['choix_g'] = "Tout le monde"

# Important : On crée une variable locale 'choix_g' qui servira aux calculs
# Elle prend la valeur actuelle de la session
choix_g = st.session_state.choix_g

if 'groupes_liste' not in st.session_state:
    # Charger tes groupes sauvegardés ici pour qu'ils apparaissent dans le sélecteur
    if os.path.exists("mes_groupes.txt"):
        with open("mes_groupes.txt", "r", encoding="utf-8") as f:
            st.session_state.groupes_liste = [l.strip() for l in f.readlines() if l.strip()]
    else:
        st.session_state.groupes_liste = []

if 'config_groupes' not in st.session_state:
    if os.path.exists("config_comptes.csv"):
        try:
            temp_df = pd.read_csv("config_comptes.csv", index_col=0, encoding='utf-8-sig')
            if "Couleur" not in temp_df.columns:
                temp_df["Couleur"] = "#1f77b4"
            temp_df["Couleur"] = temp_df["Couleur"].fillna("#1f77b4")
            st.session_state.config_groupes = temp_df.to_dict('index')
            
            for nom_compte, data in st.session_state.config_groupes.items():
                cle_picker = f"cp_{nom_compte}"
                if cle_picker not in st.session_state:
                    st.session_state[cle_picker] = data["Couleur"]
        except Exception as e:
            st.error(f"Erreur lecture config: {e}")
            st.session_state.config_groupes = {}
    else:
        st.session_state.config_groupes = {}

# --- AJOUT INDISPENSABLE ICI (En dehors du IF) ---
# On s'assure que TOUS les comptes présents dans le DataFrame actuel 
# ont une entrée dans config_groupes pour éviter le retour au bleu
if not st.session_state.df.empty:
    comptes_actuels = st.session_state.df["Compte"].unique()
    for c in comptes_actuels:
        if c not in st.session_state.config_groupes:
            # Nouveau compte détecté ! On lui donne une couleur par défaut
            st.session_state.config_groupes[c] = {"Couleur": "#1f77b4", "Groupe": "Personnel", "Solde": 0.0}
            st.session_state[f"cp_{c}"] = "#1f77b4"

# --- 3. VARIABLES DE TRAVAIL (Initialisation par défaut) ---
df_h = st.session_state.df.copy()
df_f = pd.DataFrame()
df_dash = pd.DataFrame()
df_reel = pd.DataFrame()
solde_global = 0.0
obj = 0.0
s_init = 0.0
cps = []


# --- 5. DESIGN (SORTI DU IF POUR TOUJOURS S'APPLIQUER) ---
st.markdown("""
    <style>
        .block-container { padding-top: 2rem; padding-bottom: 0rem; }
        header[data-testid="stHeader"] { background: rgba(0,0,0,0); }
    </style>
""", unsafe_allow_html=True)

# --- 2. DICTIONNAIRES ET CONSTANTES ---
CORRESPONDANCE = {
    "Date": ["Date", "Date opération", "Date de valeur", "Effective Date", "Date op", "Date val", "Le", "Date de comptabilisation","Date operation", "date"],
    "Nom": ["Nom", "Libelle simplifie", "Libellé", "Description", "Transaction", "Libellé de l'opération", "Détails", "Objet", "Type"],
    "Montant": ["Montant", "Montant(EUROS)", "Valeur", "Amount", "Prix", "Montant net", "Somme"],
    "Debit": ["Debit", "Débit"],
    "Credit": ["Credit", "Crédit"]
}

NOMS_MOIS = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]


def charger_categories_perso():
    # Liste par défaut si le fichier n'existe pas
    defaut = [
        "💰 Salaire", "🏥 Remboursements", "🤝 Virements Reçus", "👫 Compte Commun",
        "📱 Abonnements", "🛒 Alimentation", "🛍️ Shopping", "👕 Habillement", 
        "⚖️ Impôts", "🏦 Frais Bancaires", "🏠 Assurance Habitation", "🎮 Jeux vidéos",
        "🩺 Mutuelle", "💊 Pharmacie", "👨‍⚕️ Médecin/Santé", "🔑 Loyer", 
        "🔨 Bricolage", "🚌 Transports", "⛽ Carburant", "🚗 Auto", 
        "💸 Virements Perso", "🏧 Retraits", "🌐 Web/Énergie", "🔄 Transfert Interne", "❓ Autre"
    ]
    if os.path.exists("mes_categories.txt"):
        with open("mes_categories.txt", "r", encoding="utf-8") as f:
            perso = [line.strip() for line in f.readlines() if line.strip()]
            return sorted(list(set(defaut + perso))) # Fusionne et retire les doublons
    return sorted(defaut)

def sauvegarder_nouvelle_categorie(nouvelle_cat):
    cats = charger_categories_perso()
    if nouvelle_cat not in cats:
        with open("mes_categories.txt", "a", encoding="utf-8") as f:
            f.write(f"{nouvelle_cat}\n")
        return True
    return False


LISTE_CATEGORIES_COMPLETE = charger_categories_perso()

# --- 3. TOUTES LES FONCTIONS ---



def charger_memoire():
    if os.path.exists("memoire_categories.csv"):
        return pd.read_csv("memoire_categories.csv").set_index('Nom')['Categorie'].to_dict()
    return {}

def sauvegarder_apprentissage(nom_ope, categorie):
    memoire = charger_memoire()
    # On nettoie le nom pour qu'il soit générique
    nom_clean = simplifier_nom_definitif(nom_ope)
    memoire[nom_clean] = categorie
    pd.DataFrame(list(memoire.items()), columns=['Nom', 'Categorie']).to_csv("memoire_categories.csv", index=False)



def charger_couleur(nom_fichier, defaut="#1f77b4"):
    if os.path.exists(nom_fichier):
        with open(nom_fichier, "r") as f: return f.read().strip()
    return defaut

def sauvegarder_couleur(nom_fichier, hex_color):
    with open(nom_fichier, "w") as f: f.write(hex_color)

def charger_groupes():
    if os.path.exists("mes_groupes.txt"):
        with open("mes_groupes.txt", "r", encoding="utf-8") as f:
            groupes = [line.strip() for line in f.readlines() if line.strip()]
            return groupes if groupes else ["Personnel"]
    return ["Personnel"]

def sauvegarder_groupes(liste):
    with open("mes_groupes.txt", "w", encoding="utf-8") as f:
        for item in liste: f.write(f"{item}\n")

def charger_config():
    if os.path.exists("config_comptes.csv"):
        return pd.read_csv("config_comptes.csv", index_col=0).to_dict('index')
    return {}

def sauvegarder_config(config_dict):
    try:
        # 1. On tente de lire ce qui existe déjà sur le fichier pour ne rien perdre
        if os.path.exists("config_comptes.csv"):
            df_existant = pd.read_csv("config_comptes.csv", index_col=0)
            
            # On convertit le dict actuel en DataFrame
            df_nouveau = pd.DataFrame.from_dict(config_dict, orient='index')
            
            # On fusionne : le nouveau écrase l'ancien, MAIS on garde les colonnes manquantes
            for col in df_existant.columns:
                if col not in df_nouveau.columns:
                    df_nouveau[col] = df_existant[col]
            
            df_save = df_nouveau
        else:
            df_save = pd.DataFrame.from_dict(config_dict, orient='index')

        df_save.to_csv("config_comptes.csv", encoding='utf-8-sig', index=True)
    except Exception as e:
        st.error(f"Erreur sauvegarde : {e}")


# --- GARDE-FOU ANTI-RETOUR AU BLEU ---
if os.path.exists("config_comptes.csv"):
    try:
        # On lit le CSV de référence
        df_ref = pd.read_csv("config_comptes.csv", index_col=0, encoding='utf-8-sig')
        
        if "Couleur" in df_ref.columns:
            for nom_compte in st.session_state.config_groupes:
                if nom_compte in df_ref.index:
                    couleur_csv = df_ref.loc[nom_compte, "Couleur"]
                    
                    # Si la couleur en mémoire est celle par défaut ou vide, on force celle du CSV
                    memo_color = st.session_state.config_groupes[nom_compte].get("Couleur", "#1f77b4")
                    if (memo_color == "#1f77b4" or pd.isna(memo_color)) and pd.notna(couleur_csv):
                        st.session_state.config_groupes[nom_compte]["Couleur"] = couleur_csv
                        # On met aussi à jour le widget picker pour qu'il ne re-bascule pas
                        st.session_state[f"cp_{nom_compte}"] = couleur_csv
    except:
        pass


def clean_montant_physique(valeur):
    if pd.isna(valeur) or valeur == "": return 0.0
    s = str(valeur).replace('\xa0', '').replace(' ', '').replace('€', '').replace('$', '')
    if ',' in s and '.' in s: s = s.replace(',', '')
    elif ',' in s: s = s.replace(',', '.')
    try: return float(s)
    except: return 0.0

def charger_donnees():
    if os.path.exists("ma_base_de_donnees.csv"):
        try:
            # On essaie UTF-8, sinon Latin-1 pour gérer les accents
            try:
                df = pd.read_csv("ma_base_de_donnees.csv", encoding='utf-8-sig')
            except UnicodeDecodeError:
                df = pd.read_csv("ma_base_de_donnees.csv", encoding='latin-1')

            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
                df = df.dropna(subset=["Date"])
                
                # --- AJOUT CRITIQUE POUR LE DASHBOARD ---
                if "Année" not in df.columns:
                    df["Année"] = df["Date"].dt.year
                
                if "Mois" not in df.columns:
                    df["Mois"] = df["Date"].dt.month.map(lambda x: NOMS_MOIS[int(x)-1] if pd.notna(x) else "Inconnu")

            if "Montant" in df.columns:
                df["Montant"] = df["Montant"].apply(clean_montant_physique)
            
            return df
        except Exception as e:
            # En cas d'erreur, on affiche l'erreur pour déboguer
            print(f"Erreur lecture : {e}")
            return pd.DataFrame(columns=["Date", "Nom", "Montant", "Categorie", "Compte", "Mois", "Année"])
            
    return pd.DataFrame(columns=["Date", "Nom", "Montant", "Categorie", "Compte", "Mois", "Année"])

def sauvegarder_donnees(nouveau_df):
    nom_fichier = "ma_base_de_donnees.csv"
    if "Mois" not in nouveau_df.columns:
        nouveau_df["Mois"] = nouveau_df["Date"].dt.month.map(lambda x: NOMS_MOIS[int(x)-1] if pd.notna(x) else "Inconnu")
    if os.path.exists(nom_fichier):
        ancien_df = pd.read_csv(nom_fichier, encoding='utf-8-sig')
        ancien_df["Date"] = pd.to_datetime(ancien_df["Date"], errors='coerce')
        df_total = pd.concat([ancien_df, nouveau_df], ignore_index=True)
        df_total = df_total.drop_duplicates(subset=["Date", "Nom", "Montant", "Compte"])
        df_total.to_csv(nom_fichier, index=False, encoding='utf-8-sig')
    else: nouveau_df.to_csv(nom_fichier, index=False, encoding='utf-8-sig')

def simplifier_nom_definitif(nom):
    if not isinstance(nom, str): return str(nom)
    nom = nom.upper()
    nom = re.sub(r'(FAC|REF|NUM|ID|PRLV|VIREMENT)\s*[:.\-]?\s*[0-9A-Z]+', '', nom)
    nom = re.sub(r'\d{2}[\./]\d{2}([\./]\d{2,4})?', '', nom)
    for m in ["ACHAT CB", "ACHAT", "CB", "CARTE", "VERSEMENT", "CHEQUE", "SEPA"]: nom = nom.replace(m, "")
    return ' '.join(re.sub(r'[\*\-\/#]', ' ', nom).split()).strip() or "AUTRE"

def categoriser(nom_operation, montant=0, compte_actuel=None, ligne_complete=None):
    n_brut = str(nom_operation).upper()
    n_clean = simplifier_nom_definitif(n_brut)
    
    mots_transfert = [
        "VIREMENT VERS COMPTE CHEQUES", "VIREMENT VERS LIVRET A","Virement interne"
    ]

    # --- ÉTAPE 1 : Scan du libellé principal ---
    est_transfert = any(m in n_brut for m in mots_transfert)

    # --- ÉTAPE 2 : Scan de TOUTES les colonnes du CSV ---
    if not est_transfert and ligne_complete is not None:
        # On récupère toutes les valeurs de la ligne, on les transforme en texte, 
        # on les met en majuscules et on colle tout avec un espace.
        texte_complet_ligne = " ".join([str(v).upper() for v in ligne_complete.values])
        
        # On vérifie si un de nos mots-clés est n'importe où dans ce texte
        if any(m in texte_complet_ligne for m in mots_transfert):
            est_transfert = True

    if est_transfert:
        return "🔄 Transfert Interne"

    # ... reste de la fonction (mémoire, puis catégories)

    # --- 2. VÉRIFICATION DE LA MÉMOIRE (Apprentissage) ---
    memoire = charger_memoire()
    if n_clean in memoire:
        return memoire[n_clean]
    

    # --- 3. TES CATÉGORIES HABITUELLES ---
    CATEGORIES_MOTS_CLES = {
        "💰 Salaire": ["MELTED", "JEFF DB", "FRANCE TRAVAIL", "POLE EMPLOI", "SARL","JEFF DE BRUGES"],
        "🏥 Remboursements": ["NOSTRUMCARE", "AMELI", "CPAM", "REMBOURSEMENT", "SANTÉ","FAUSTINE BOJUC"],
        "👫 Compte Commun": ["A FONTA AUDE OU LEBARBIER THEO","AUDE FONTATHEO LEBARBIE", "VERSEMENT COMMUN", "VIREMENT COMMUN"],
        "🤝 Virements Reçus": ["LEBARBIER THEO", "LEBARBIER DIDIER", "MARYLINE FONTA", "AURORE FONTA", "MME AUDE FONTA","DE MR LEBARBIER D"],
        "📱 Abonnements": ["NETFLIX", "SPOTIFY", "DISNEY PLUS", "AMAZON PRIME", "YOUTUBE PREMIUM", "ORANGE", "GOOGLE PLAY", "GOOGLE ONE", "AMZ DIGITAL", "TWITCH"],
        "🛒 Alimentation": ["CARREFOUR", "AUCHAN", "MONOPRIX", "CASINO", "SUPER", "PICARD", "BIOCOOP", "MARCHE", "BOULANGERIE", "RESTAURANT", "BAR", "MCDO", "SUBWAY", "INTERMARCHE", "LECLERC","AUTOGRILL","PROZIS","CIAO BELLA"],
        "🛍️ Shopping": ["AMAZON", "FNAC", "DARTY", "CULTURA", "ZARA", "H&M", "KIABI", "KLARNA"],
        "👕 Habillement": ["VETEMENTS", "CHAUSSURES", "MODE", "CELIO", "JULES", "ASOS"],
        "⚖️ Impôts": ["IMPOTS", "TRESOR PUBLIC", "DGFIP"],
        "🏦 Frais Bancaires": ["COTISATION BANCAIRE", "FRAIS BANCAIRES", "COTISATION ESSENTIEL"],
        "🏠 Assurance Habitation": ["PACIFICA", "MMA", "MAIF", "MACIF"],
        "🎮 Jeux vidéos": ["SONY PLAYSTATION", "NINTENDO", "STEAM", "EPIC GAMES", "INSTANT GAMING"],
        "🩺 Mutuelle": ["MUTUELLE", "HARMONIE", "MGEN", "NOSTRUM CARE"],
        "💊 Pharmacie": ["PHARMACIE", "MÉNARD", "PHARMA"],
        "👨‍⚕️ Médecin/Santé": ["MEDECIN", "DENTISTE", "DOCTOLIB"],
        "🔑 Loyer": ["LOYER", "AGENCE IMMOBILIERE", "Jason Moliner","JASON MOLINER"],
        "🔨 Bricolage": ["CASTORAMA", "LEROY", "BRICO DEPOT", "IKEA"],
        "🚌 Transports": ["RATP", "SNCF", "TCL", "ORIZO"],
        "⛽ Carburant": ["TOTAL", "BP", "ESSENCE", "SHELL", "ESSOF", "CERTAS","STATION"],
        "🚗 Auto": ["CREDIT AUTO", "GARAGE", "REPARATION", "AUTO"],
        "💸 Virements Perso": ["VIREMENT A", "VIREMENT INSTANTANE", "VIR SEPA"],
        "🏧 Retraits": ["RETRAIT DAB", "RETRAIT GAB"],
        "🌐 Web/Énergie": ["FREE", "SFR", "BOUYGUES", "EDF", "ENGIE"],
    }
    
    for cat, mots in CATEGORIES_MOTS_CLES.items():
        if any(m in n_brut for m in mots): return cat
    
    return "💰 Autres Revenus" if montant > 0 else "❓ Autre"

# --- 4. INITIALISATION ---
if 'df' not in st.session_state: st.session_state.df = charger_donnees()
if 'config_groupes' not in st.session_state: st.session_state.config_groupes = charger_config()
if 'groupes_liste' not in st.session_state: st.session_state.groupes_liste = charger_groupes()

# --- 1. On récupère les comptes qui ont déjà des transactions ---
comptes_avec_data = st.session_state.df["Compte"].unique().tolist() if not st.session_state.df.empty else []

# --- 2. On récupère TOUS les comptes configurés dans ton fichier config ---
comptes_configures = []
if os.path.exists("config_comptes.csv"):
    try:
        df_cfg = pd.read_csv("config_comptes.csv", encoding='utf-8-sig')
        # On suppose que le nom du compte est dans la première colonne
        comptes_configures = df_cfg.iloc[:, 0].unique().tolist()
    except:
        pass

# --- 3. On fusionne les deux listes (sans doublons) pour la liste déroulante ---
comptes_detectes = sorted(list(set(comptes_avec_data + comptes_configures)))
bg_color_saved = st.session_state.get('page_bg_color', "#0e1117")
# --- 5. SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Configuration")

    st.subheader("🎨 Réglages du Thème")

    col_patri = st.color_picker("Évolution Patrimoine", charger_couleur("color_patrimoine.txt", "#1f77b4"))
    sauvegarder_couleur("color_patrimoine.txt", col_patri)
    
    col_jauge = st.color_picker("Jauge Objectif", charger_couleur("color_jauge.txt", "#f1c40f"))
    sauvegarder_couleur("color_jauge.txt", col_jauge)
    
    col_dep = st.color_picker("Barres des dépenses", charger_couleur("color_depenses.txt", "#e74c3c"))
    sauvegarder_couleur("color_depenses.txt", col_dep)
    
    col_rev = st.color_picker("Aires des Revenus", charger_couleur("color_revenus.txt", "#2ecc71"))
    sauvegarder_couleur("color_revenus.txt", col_rev)
    
    col_perf_dep = st.color_picker("Aires des Dépenses", charger_couleur("color_perf_dep.txt", "#e74c3c"))
    sauvegarder_couleur("color_perf_dep.txt", col_perf_dep)

    col_epargne = st.color_picker("Aires de l'Épargne", charger_couleur("color_epargne.txt", "#3498db"))
    sauvegarder_couleur("color_epargne.txt", col_epargne)

    col_Icones = st.color_picker("Icones menus", charger_couleur("color_icones", "#15C98D"))
    sauvegarder_couleur("color_epargne.txt", col_Icones)
   
   
    toutes_cats = sorted(st.session_state.df["Categorie"].unique().tolist()) if not st.session_state.df.empty else []

      # 1. On charge la couleur depuis le fichier (ou gris foncé par défaut)
    bg_color = st.color_picker(
        "Couleur de fond", 
        charger_couleur("color_background.txt", "#0e1117")
    )
    
    # 2. On sauvegarde immédiatement le choix
    sauvegarder_couleur("color_background.txt", bg_color)

    # --- 3. INJECTION DU CSS POUR APPLIQUER LA COULEUR ---
    st.markdown(f"""
        <style>
        .stApp {{
            background-color: {bg_color};
        }}
        </style>
        """, unsafe_allow_html=True)

    st.subheader("🎨 Couleurs des comptes")
    
        # On récupère tous les comptes présents dans le DF actuel + ceux configurés
    comptes_actifs = []
    if not st.session_state.df.empty:
        comptes_actifs = st.session_state.df["Compte"].unique().tolist()
        
    # Union des comptes du fichier config et des comptes du DF
    tous_les_comptes = sorted(list(set(list(st.session_state.config_groupes.keys()) + comptes_actifs)))

    for c in tous_les_comptes:
        if c not in st.session_state.config_groupes:
            st.session_state.config_groupes[c] = {"Couleur": "#1f77b4", "Groupe": "Personnel", "Solde": 0.0}
        
        current_val = st.session_state.config_groupes[c].get("Couleur", "#1f77b4")
        
        # Sécurité anti-corruption (NaN)
        if not isinstance(current_val, str) or not current_val.startswith("#"):
            current_val = "#1f77b4"

        # --- CORRECTION ICI ---
        # On initialise la clé du widget AVANT l'affichage si elle n'existe pas
        cle_widget = f"cp_{c}"
        if cle_widget not in st.session_state:
            st.session_state[cle_widget] = current_val

        st.color_picker(
            f"Couleur : {c}", 
            # On ne met plus 'value' car Streamlit utilisera automatiquement 
            # la valeur de st.session_state[cle_widget]
            key=cle_widget,
            on_change=update_couleur_compte,
            args=(c,)
        )
            



# --- BARRE DE NAVIGATION CAMOUFLÉE ---
selected = option_menu(
    menu_title=None,
    options=["Analyses", "Gestion", "Import", "Groupes"],
    icons=["bar-chart-line-fill", "table", "file-earmark-spreadsheet-fill", "person-fill-gear"], 
    default_index=0, # 0 correspond à "Analyses"
    orientation="horizontal",
    styles={
        "container": {
            "padding": "0px !important", 
            "background-color": "#012523 !important", # Ta couleur de page
            "border": "none !important"
        },
        "icon": {
            "color": col_Icones, 
            "font-size": "25px"
        },
        "nav-link": {
            "font-size": "11px",
            "background-color": "#012523 !important", # Ta couleur de page
            "color": "#ffffff7f",
            "font-weight": "bold",
            "border": "none !important",
            "display": "flex",
            "flex-direction": "column",
            "align-items": "center",
            "font-size": "15px",
            "border-radius": "15px",  # C'est ici qu'on arrondit les angles
            "width": "100px",          # On force une largeur fixe pour faire un carré
            "height": "80px",
        },
        "nav-link-selected": {
            "background-color": "rgba(255, 255, 255, 0.05) !important", # Un voile très léger pour distinguer l'onglet
            "color": "#ffffff", 
            "font-weight": "bold",
            "font-size": "15px"
            
        },
    }
)

st.markdown("""
<style>
    /* 1. On supprime le fond noir de TOUS les conteneurs de blocs sur cette page */
    div[data-testid="stVerticalBlock"], 
    div[data-testid="stVerticalBlockBorderWrapper"],
    div[data-testid="stCustomComponentV1"] {
        background-color: #012523 !important;
        background: #012523 !important;
    }

    /* 2. On cible l'iframe spécifiquement pour qu'il n'ait aucune marge */
    iframe[title="streamlit_option_menu.option_menu"] {
        width: 100% !important;
        background-color: #012523 !important;
    }

    /* 3. On élimine le padding interne de Streamlit qui crée ces zones noires */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0rem !important;
    }
</style>
""", unsafe_allow_html=True)






# --- LOGIQUE D'AFFICHAGE (Routage) ---
if selected == "Analyses":
    # --- 6. TAB DASHBOARD ---
        if not st.session_state.df.empty:
            # On s'assure que la colonne Année existe dans le DataFrame
            if "Année" not in st.session_state.df.columns:
                st.session_state.df["Année"] = st.session_state.df["Date"].dt.year

            # 1. LES SÉLECTEURS (Profil, Année, Mois)
            cols_filtres = st.columns([1, 1, 1, 1])
            
            with cols_filtres[0]:
                st.selectbox(
                    "🎯 Profil actif :", 
                    ["Tout le monde"] + st.session_state.groupes_liste,
                    key="choix_g" 
                )

            # --- LOGIQUE DE FILTRAGE PAR PROFIL ---
            choix_actuel = st.session_state.choix_g
            df_h = st.session_state.df.copy()

            if choix_actuel != "Tout le monde":
                cps = [c for c, cfg in st.session_state.config_groupes.items() if cfg.get("Groupe") == choix_actuel]
                df_dash = df_h[df_h["Compte"].isin(cps)].copy()
                s_init = sum([v.get("Solde", 0.0) for k, v in st.session_state.config_groupes.items() if k in cps])
                obj = sum([v.get("Objectif", 0.0) for k, v in st.session_state.config_groupes.items() if v.get("Groupe") == choix_actuel])
            else:
                cps = list(st.session_state.config_groupes.keys())
                df_dash = df_h.copy()
                s_init = sum([v.get("Solde", 0.0) for v in st.session_state.config_groupes.values()])
                obj = sum([v.get("Objectif", 0.0) for v in st.session_state.config_groupes.values()])

            # --- NOUVEAU : FILTRAGE PAR ANNÉE ---
            liste_annees = sorted(df_dash['Année'].unique().tolist(), reverse=True)
            with cols_filtres[1]:
                annee_choisie = st.selectbox("📅 Année :", liste_annees)
            
            # On affine df_dash avec l'année choisie
            df_dash = df_dash[df_dash["Année"] == annee_choisie]

            # --- FILTRAGE PAR MOIS ---
            liste_m = sorted(df_dash['Mois'].unique(), key=lambda x: NOMS_MOIS.index(x) if x in NOMS_MOIS else 0)
            with cols_filtres[2]:
                mois_choisi = st.selectbox("📆 Mois :", liste_m)

            # Calculs finaux basés sur les filtres Profil + Année
            solde_global = s_init + df_dash["Montant"].sum()
            df_reel = df_dash[~df_dash["Categorie"].isin(["Virement Perso", "Transfert Interne"])].copy()

            st.write(f"#### 🏦 Situation Financière : {choix_g}")
            col_Card = "#3498db"
            cols_kpi = st.columns(len(cps) + 1)

            # --- 1. CARTE SOLDE GLOBAL ---
            with cols_kpi[0]:
                st.markdown(f"""
                    <div style="background-color: {col_patri}; padding: 15px; border-radius: 12px; text-align: center; box-shadow: 2px 2px 5px rgba(0,0,0,0.1);">
                        <p style="margin: 0; font-size: 12px; color: white; font-weight: bold; text-transform: uppercase;">💰 Solde Global</p>
                        <p style="margin: 0; font-size: 20px; color: white; font-weight: 800;">{solde_global:,.0f} €</p>
                    </div>
                """, unsafe_allow_html=True)

            # --- 2. CARTES DES COMPTES INDIVIDUELS ---
            config_master = st.session_state.get('config_groupes', {})

            for i, c in enumerate(cps):
                # NETTOYAGE : On enlève les espaces invisibles
                nom_propre = str(c).strip()
                
                # Calcul du solde
                val = config_master.get(nom_propre, {}).get("Solde", 0.0) + df_dash[df_dash["Compte"] == nom_propre]["Montant"].sum()
                
                # RÉCUPÉRATION : On essaie d'abord le dictionnaire en mémoire
                couleur_compte = config_master.get(nom_propre, {}).get("Couleur")

                # Si absent du dict, on tente une relecture du CSV avec sécurité anti-KeyError
                if not couleur_compte and os.path.exists("config_comptes.csv"):
                    try:
                        df_c = pd.read_csv("config_comptes.csv", index_col=0, encoding='utf-8-sig')
                        # VÉRIFICATION SÉCURISÉE (Évite le crash KeyError)
                        if nom_propre in df_c.index and "Couleur" in df_c.columns:
                            val_csv = df_c.loc[nom_propre, "Couleur"]
                            if pd.notna(val_csv):
                                couleur_compte = val_csv
                    except Exception:
                        pass # On ignore l'erreur pour ne pas bloquer l'affichage

                # Sécurité finale si toujours rien (on utilise le bleu par défaut)
                if not isinstance(couleur_compte, str) or pd.isna(couleur_compte) or not str(couleur_compte).startswith("#"):
                    couleur_compte = col_Card

                with cols_kpi[i+1]:
                    st.markdown(f"""
                        <div style="background-color: {couleur_compte}; padding: 15px; border-radius: 12px; text-align: center; box-shadow: 2px 2px 5px rgba(0,0,0,0.1);">
                            <p style="margin: 0; font-size: 11px; color: white; font-weight: bold; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; text-transform: uppercase;">{nom_propre}</p>
                            <p style="margin: 0; font-size: 18px; color: white; font-weight: 700;">{val:,.0f} €</p>
                        </div>
                    """, unsafe_allow_html=True)

            # Données Annuelles (Mots entiers et Épargne)
            annee_max = df_dash['Date'].dt.year.max()
            df_ann = df_reel[df_dash['Date'].dt.year == annee_max].groupby('Mois').agg(
                Revenus=('Montant', lambda x: x[x > 0].sum()),
                Dépenses=('Montant', lambda x: abs(x[x < 0].sum()))
            ).reset_index()
            # 1. On crée la base du tableau avec les mois
            df_tab = pd.DataFrame({'Mois': NOMS_MOIS})

            # 2. On calcule le cumulé pour CHAQUE compte du groupe sélectionné
            for c in cps:
                # On récupère le solde initial de ce compte précis
                s_init_compte = st.session_state.config_groupes[c].get("Solde", 0.0)
                
                # On calcule les mouvements mensuels pour ce compte
                mouvements = df_dash[df_dash["Compte"] == c].groupby("Mois")["Montant"].sum().reset_index()
                
                # On fusionne avec les mois pour avoir les 12 mois, même sans mouvements
                df_c = pd.merge(pd.DataFrame({'Mois': NOMS_MOIS}), mouvements, on='Mois', how='left').fillna(0)
                
                # On crée la colonne du compte avec son cumul
                df_tab[c] = s_init_compte + df_c["Montant"].cumsum()

            # 3. On recrée les colonnes globales pour tes autres graphiques
            # On récupère aussi Revenus/Dépenses depuis df_ann pour garder tes autres stats
            df_tab = pd.merge(df_tab, df_ann[['Mois', 'Revenus', 'Dépenses']], on='Mois', how='left').fillna(0)
            df_tab['Épargne'] = df_tab['Revenus'] - df_tab['Dépenses']

            # Le patrimoine total est maintenant la somme exacte des comptes du groupe
            df_tab['Patrimoine'] = df_tab[cps].sum(axis=1)


            c_recap, c_ann, c_graph = st.columns([1, 1, 1])

            with c_recap:
        # 1. Utilisation de Markdown au lieu de subheader pour un contrôle total des marges
                st.markdown(f"""
                    <h3 style='margin-bottom: 0px; padding-bottom: 0px;'>
                        📋 Détails {mois_choisi} {annee_choisie}
                    </h3>
                """, unsafe_allow_html=True)
                
                # 2. CSS compact étendu
                st.markdown("""
                    <style>
                    /* Supprime l'espace vertical entre les blocs Streamlit dans cette colonne */
                    [data-testid="stVerticalBlock"] > div {
                        gap: 0rem !important;
                    }
                    
                    /* Compactage des onglets */
                    button[data-baseweb="tab"] {
                        padding-left: 00px !important;
                        padding-right: 10px !important;
                        gap: 4px !important;
                        margin-top: 0px !important;
                    }
                    
                    /* Réduit l'espace au-dessus du conteneur d'onglets */
                    div[data-testid="stTabs"] {
                        margin-top: 0px !important;
                    }
                    </style>
                """, unsafe_allow_html=True)

                # 1. DÉFINITION DE LA FONCTION (Inchangée)
                def afficher_ligne_compacte(row, couleur_montant, prefixe=""):
                    ico = row['Categorie'][:1] if row['Categorie'] else "💰"
                    if prefixe == "🔄": ico = "🔄"
                    st.markdown(f"""
                        <div style="display: flex; align-items: center; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid #f0f2f6;">
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <span style="font-size: 15px;">{ico}</span>
                                <div>
                                    <p style="margin: 0; font-weight: bold; font-size: 12px; line-height: 1.1;">{row['Nom']}</p>
                                    <p style="margin: 0; font-size: 10px; color: gray;">{row['Date'].strftime('%d/%m')} • {row['Compte']}</p>
                                </div>
                            </div>
                            <div style="text-align: right;">
                                <p style="margin: 0; color: {couleur_montant}; font-weight: bold; font-size: 12px;">{prefixe}{abs(row['Montant']):.2f}€</p>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                # 2. PRÉPARER LES DONNÉES 
                # SÉCURITÉ : On filtre par Mois ET par Année pour être certain
                df_m = df_dash[(df_dash['Mois'] == mois_choisi) & (df_dash['Année'] == annee_choisie)].sort_values("Date", ascending=False)
                
                cats_masquees = ["Virement Perso", "Transfert Interne", "Virement interne", "🔄 Transfert Interne"]
                is_vir = df_m['Categorie'].str.upper().isin([c.upper() for c in cats_masquees])

                df_virs = df_m[is_vir]
                df_dep = df_m[(df_m['Montant'] < 0) & (~is_vir)]
                df_rev = df_m[(df_m['Montant'] > 0) & (~is_vir)]

                # 3. ONGLETS COMPACTS
                t_dep, t_rev, t_vir, t_graph = st.tabs([
                    f"Dépenses ({len(df_dep)})", 
                    f"Revenus ({len(df_rev)})", 
                    f"Transferts({len(df_virs)})",
                    "Analyses"
                ])

                with t_dep:
                    with st.container(height=430):
                        for _, row in df_dep.iterrows(): afficher_ligne_compacte(row, "#ff4b4b", "-")
                
                with t_rev:
                    with st.container(height=430):
                        for _, row in df_rev.iterrows(): afficher_ligne_compacte(row, "#00c853", "+")
                
                with t_vir:
                    with st.container(height=430):
                        for _, row in df_virs.iterrows(): afficher_ligne_compacte(row, "gray", "")

                with t_graph:
                    virements_techniques = ["Virement Perso", "Transfert Interne", "Virement interne", "🔄 Transfert Interne"]
                    # On utilise df_dash pour les options du multiselect afin d'avoir toutes les catégories de l'année
                    categories_a_masquer = st.sidebar.multiselect("Catégories à masquer", options=sorted(df_dash['Categorie'].unique()), key="mask_recap")
                    
                    liste_exclusion = virements_techniques + categories_a_masquer
                    df_b = df_m[(df_m['Montant'] < 0) & (~df_m['Categorie'].isin(liste_exclusion))]
                    
                    if not df_b.empty:
                        df_res = df_b.groupby("Categorie")["Montant"].sum().abs().reset_index().sort_values("Montant")
                        fig_b = px.bar(df_res, x="Montant", y="Categorie", orientation='h')
                        
                        max_val = df_res["Montant"].max()
                        fig_b.update_traces(
                            marker_color=col_perf_dep, 
                            texttemplate='%{x:.0f} €',
                            textposition='outside', 
                            textfont=dict(size=10, color="gray")
                        )
                        fig_b.update_layout(
                            height=400, 
                            margin=dict(l=0, r=50, t=10, b=0), 
                            xaxis=dict(showgrid=False, visible=False, range=[0, max_val * 1.3]),
                            yaxis=dict(showgrid=False, tickfont=dict(color="gray")),
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)'
                        )
                        st.plotly_chart(fig_b, use_container_width=True, config={'displayModeBar': False})
                    else:
                        st.info("Aucune dépense à analyser pour cette période.")





            with c_ann:
                st.subheader(f"🗓️ Récapitulatif {annee_choisie}")
                
                if not df_dash.empty:
                    # 1. On crée le récap par mois existants
                    df_reel_mois = df_dash.groupby('Mois')['Montant'].agg(
                        Revenus=lambda x: x[x > 0].sum(),
                        Dépenses=lambda x: abs(x[x < 0].sum())
                    ).reset_index()

                    # 2. CRÉATION DE LA STRUCTURE COMPLÈTE (Jan à Déc)
                    # On crée un DataFrame avec tous les mois de ta liste NOMS_MOIS
                    df_template = pd.DataFrame({'Mois': NOMS_MOIS})
                    
                    # On fusionne le template avec les données réelles
                    df_tab = pd.merge(df_template, df_reel_mois, on='Mois', how='left').fillna(0)

                    # 3. On calcule l'épargne mensuelle
                    df_tab['Épargne'] = df_tab['Revenus'] - df_tab['Dépenses']
                    
                    # 4. Tri chronologique (basé sur l'ordre de NOMS_MOIS)
                    df_tab['Mois_idx'] = df_tab['Mois'].apply(lambda x: NOMS_MOIS.index(x))
                    df_tab = df_tab.sort_values('Mois_idx')

                    # 5. Calcul du Patrimoine cumulé
                    # Le cumsum() fonctionnera sur les 12 mois, gardant le solde stable si l'épargne est à 0
                    df_tab['Patrimoine'] = s_init + df_tab['Épargne'].cumsum()

                    # --- AFFICHAGE DU TABLEAU ---
                    h1, h2, h3, h4, h5 = st.columns([1.2, 1, 1, 1.2, 1.3])
                    base_h = "margin:0; font-weight:bold; font-size:10px; color:gray;"
                    
                    h1.markdown(f"<p style='{base_h} text-align:Center;'>MOIS</p>", unsafe_allow_html=True)
                    h2.markdown(f"<p style='{base_h} text-align:Center;'>REVENUS</p>", unsafe_allow_html=True)
                    h3.markdown(f"<p style='{base_h} text-align:Center;'>DÉPENSES</p>", unsafe_allow_html=True)
                    h4.markdown(f"<p style='{base_h} text-align:Center;'>ÉPARGNE</p>", unsafe_allow_html=True)
                    h5.markdown(f"<p style='{base_h} text-align:Center;'>SOLDE</p>", unsafe_allow_html=True)

                    st.markdown("<div style='margin-top: -10px;'></div>", unsafe_allow_html=True)
                    
                    with st.container(height=450):
                        for _, row in df_tab.iterrows():
                            # On n'affiche la ligne que si c'est un mois passé ou s'il y a de l'activité
                            # (Optionnel : si tu veux vraiment voir les 12 mois même futurs, enlève toute condition)
                            
                            c1, c2, c3, c4, c5 = st.columns([1.2, 1, 1, 1.2, 1.3])
                            
                            color_ep = col_epargne if row['Épargne'] >= 0 else "#ff4b4b"
                            base_d = "margin:0; font-weight:bold; font-size:13px;"
                            
                            # Style gris pour les mois à 0 (facultatif)
                            opacity = "1.0" if (row['Revenus'] > 0 or row['Dépenses'] > 0) else "0.4"
                            
                            c1.markdown(f"<p style='{base_d} text-align:left; opacity:{opacity};'>{row['Mois']}</p>", unsafe_allow_html=True)
                            c2.markdown(f"<p style='{base_d} text-align:right; color:{col_rev}; opacity:{opacity};'>{row['Revenus']:,.0f}€</p>", unsafe_allow_html=True)
                            c3.markdown(f"<p style='{base_d} text-align:right; color:{col_perf_dep}; opacity:{opacity};'>{row['Dépenses']:,.0f}€</p>", unsafe_allow_html=True)
                            c4.markdown(f"<p style='{base_d} text-align:right; color:{color_ep}; opacity:{opacity};'>{row['Épargne']:,.0f}€</p>", unsafe_allow_html=True)
                            c5.markdown(f"<p style='{base_d} text-align:right; color:{col_patri};'>{row['Patrimoine']:,.0f}€</p>", unsafe_allow_html=True)
                            
                            st.markdown("<hr style='margin: 4px 0; border: 0.1px solid #f8f9fb;'>", unsafe_allow_html=True)
                else:
                    st.info(f"Aucune donnée pour l'année {annee_choisie}.")

            with c_graph:
                    st.subheader("📊 Analyses")
                    
                    # --- 1. Objectif (Hyper compact) ---
                    if obj > 0:
                        prog = min(solde_global / obj, 1.0)
                        # On met le titre et le pourcentage sur la même ligne pour gagner de la place
                        c_t1, c_t2 = st.columns([2, 1])
                        c_t1.markdown(f"**Objectif d'épargne**")
                        c_t2.markdown(f"<p style='text-align:right; margin:0; font-size:12px;'>{prog:.1%} de {obj:,.0f}€</p>", unsafe_allow_html=True)
                        
                        st.markdown(f"""
                            <div style="background:#e0e0e0; border-radius:5px; height:12px; margin-bottom:10px;">
                                <div style="background:{col_jauge}; width:{prog*100}%; height:12px; border-radius:5px;"></div>
                            </div>""", unsafe_allow_html=True)
                        
                        # On complète df_tab avec les colonnes de chaque compte pour le graphique d'évolution
                    for c in cps:
                        nom_c = str(c).strip()
                        # Calcul du flux mensuel par compte
                        df_c = df_dash[df_dash['Compte'] == nom_c].groupby('Mois')['Montant'].sum().reset_index()
                        df_c.columns = ['Mois', nom_c]
                        
                        # Fusion avec le tableau principal
                        df_tab = pd.merge(df_tab, df_c, on='Mois', how='left').fillna(0)
                        
                        # Calcul du solde progressif pour ce compte précis
                        # Solde initial du compte + cumul des flux de l'année
                        s_init_c = st.session_state.config_groupes.get(nom_c, {}).get("Solde", 0.0)
                        if nom_c in df_tab.columns:
                            df_tab[nom_c] = s_init_c + df_tab[nom_c].cumsum()
                        else:
                            # Si le compte n'a pas de mouvements, son solde reste le solde initial
                            df_tab[nom_c] = s_init_c

                # --- 2. Flux Mensuels (Avec Dégradé Vertical) ---
                    fig_p = go.Figure()

                            # Fonction interne pour générer le dégradé à la volée pour chaque trace
                    def appliquer_gradient(couleur_hex):
                                hex_c = couleur_hex.lstrip('#')
                                r, g, b = tuple(int(hex_c[i:i+2], 16) for i in (0, 2, 4))
                                return dict(
                                    type='vertical',
                                    colorscale=[
                                        (0, f'rgba({r},{g},{b},0)'),   # 0% en bas
                                        (1, f'rgba({r},{g},{b},0.6)') # 60% en haut
                                    ]
                                )

                            # Ajout des traces avec le dégradé
                    fig_p.add_trace(go.Scatter(
                                x=df_tab["Mois"], y=df_tab["Revenus"], name="Rev.", 
                                fill='tozeroy', 
                                line=dict(color=col_rev, width=2),
                                fillgradient=appliquer_gradient(col_rev)
                            ))

                    fig_p.add_trace(go.Scatter(
                                x=df_tab["Mois"], y=df_tab["Dépenses"], name="Dép.", 
                                fill='tozeroy', 
                                line=dict(color=col_perf_dep, width=2),
                                fillgradient=appliquer_gradient(col_perf_dep)
                            ))

                    fig_p.add_trace(go.Scatter(
                                x=df_tab["Mois"], y=df_tab["Épargne"], name="Épar.", 
                                fill='tozeroy', 
                                line=dict(color=col_epargne, width=2),
                                fillgradient=appliquer_gradient(col_epargne)
                            ))

                    fig_p.update_layout(
                                title=dict(text=f"Flux {annee_choisie} : {choix_actuel}", font=dict(size=14, color="white")),
                                height=180, 
                                margin=dict(l=0, r=0, t=40, b=0),
                                hovermode="x unified",
                                showlegend=True,
                                paper_bgcolor='rgba(0,0,0,0)', 
                                plot_bgcolor='rgba(0,0,0,0)',
                                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10, color="gray")),
                                xaxis=dict(showgrid=False, tickfont=dict(size=10, color="gray")),
                                yaxis=dict(showgrid=False, visible=False)
                            )

                    st.plotly_chart(fig_p, use_container_width=True, config={'displayModeBar': False},key=f"flux_{choix_actuel}_{annee_choisie}")
                            


                                        # --- PRÉPARATION DES DONNÉES PAR COMPTE ---
                    for c in cps:
                            nom_c = str(c).strip()
                            df_mouv = df_dash[df_dash['Compte'] == nom_c].groupby('Mois')['Montant'].sum().reset_index()
                            df_mouv.columns = ['Mois', 'Mouv_Mois']
                            df_tab = pd.merge(df_tab, df_mouv, on='Mois', how='left').fillna(0)
                            
                            solde_initial_historique = st.session_state.config_groupes.get(nom_c, {}).get("Solde", 0.0)
                            mouvements_passes = st.session_state.df[
                                (st.session_state.df['Compte'] == nom_c) & 
                                (st.session_state.df['Année'] < annee_choisie)
                            ]['Montant'].sum()
                            
                            solde_au_depart = solde_initial_historique + mouvements_passes
                            df_tab[nom_c] = solde_au_depart + df_tab['Mouv_Mois'].cumsum()
                            df_tab = df_tab.drop(columns=['Mouv_Mois'])


                        # --- 3. Évolution Patrimoine (Dynamique avec Transparence) ---
                    fig_e = go.Figure()

                    if os.path.exists("config_comptes.csv"):
                            df_config_file = pd.read_csv("config_comptes.csv", index_col=0, encoding='utf-8-sig')
                            config_master = df_config_file.to_dict(orient='index')
                    else:
                            config_master = st.session_state.get('config_groupes', {})

                    for c in cps:
                            nom_c = str(c).strip()
                            if nom_c in df_tab.columns:
                                couleur_hex = config_master.get(nom_c, {}).get("Couleur", "#1f77b4")
                                if not isinstance(couleur_hex, str) or pd.isna(couleur_hex):
                                    couleur_hex = "#1f77b4"

                                # Conversion HEX vers RGB pour le dégradé
                                hex_c = couleur_hex.lstrip('#')
                                r, g, b = tuple(int(hex_c[i:i+2], 16) for i in (0, 2, 4))
                                
                                # On définit la couleur de départ (60% opacité) et de fin (0% opacité)
                                c_start = f'rgba({r}, {g}, {b}, 0.6)'
                                c_stop = f'rgba({r}, {g}, {b}, 0.0)'

                                fig_e.add_trace(go.Scatter(
                                    x=df_tab["Mois"], 
                                    y=df_tab[nom_c], 
                                    name=nom_c, 
                                    stackgroup='one', 
                                    line=dict(color=couleur_hex, width=1.5),
                                    # --- CONFIGURATION DU DÉGRADÉ ---
                                    fillgradient=dict(
                                        type='vertical', # Dégradé de haut en bas
                                        colorscale=[(0, c_stop), (1, c_start)] # 0 est le bas, 1 est le haut
                                    ),
                                    hoverinfo='x+y+name'
                                ))
                                    
                        # Ajout du TOTAL (Ligne pointillée)
                    fig_e.add_trace(go.Scatter(
                            x=df_tab["Mois"], 
                            y=df_tab["Patrimoine"], 
                            name="TOTAL", 
                            line=dict(color=col_patri, width=3, dash='dot')
                        ))

                    fig_e.update_layout(
                            title=dict(text=f"Évolution comptes {annee_choisie} : {choix_actuel}", font=dict(size=14, color="white")),
                            height=300, 
                            margin=dict(l=0, r=0, t=40, b=0),
                            hovermode="x unified",
                            showlegend=True,
                            xaxis=dict(showgrid=False, tickfont=dict(color="gray")),
                            yaxis=dict(showgrid=False, visible=False),
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            legend=dict(orientation="h", yanchor="bottom", y=0.93, xanchor="right", x=1, font=dict(color="gray", size=10))
                        )

                    st.plotly_chart(fig_e, use_container_width=True, config={'displayModeBar': False},key=f"patri_{choix_actuel}_{annee_choisie}")
                                        
    
            
elif selected == "Gestion":
        st.markdown("""
            <div style="background-color: rgba(255, 255, 255, 0.05); padding: 20px; border-radius: 15px; border: 1px solid rgba(128, 128, 128, 0.1); margin-bottom: 20px;">
                <h2 style="margin: 0; font-size: 24px;">👥 Structure & Comptes</h2>
                <p style="color: gray; font-size: 14px;">Organisez vos finances par groupes et configurez vos soldes de départ.</p>
            </div>
        """, unsafe_allow_html=True)

        # --- SECTION 1 : ARCHITECTURE (GROUPES & NOUVEAUX COMPTES) ---
        col_left, col_right = st.columns(2, gap="large")

        with col_left:
            with st.expander("📁 Gestion des Groupes", expanded=False):
                st.info("Les groupes permettent de segmenter votre patrimoine (ex: Épargne, Crypto, Courant).")
                n_g = st.text_input("Nom du groupe", placeholder="Ex: Vacances", key="add_grp_input_unique")
                if st.button("➕ Ajouter le groupe", use_container_width=True):
                    if n_g and n_g not in st.session_state.groupes_liste:
                        st.session_state.groupes_liste.append(n_g)
                        sauvegarder_groupes(st.session_state.groupes_liste)
                        st.toast(f"Groupe '{n_g}' ajouté !")
                        st.rerun()
                
                st.divider()
                g_del = st.selectbox("Supprimer un groupe", st.session_state.groupes_liste)
                if st.button("🗑️ Supprimer", use_container_width=True, type="secondary"):
                    if len(st.session_state.groupes_liste) > 1:
                        st.session_state.groupes_liste.remove(g_del)
                        sauvegarder_groupes(st.session_state.groupes_liste)
                        st.warning(f"Groupe '{g_del}' supprimé")
                        st.rerun()

        with col_right:
            with st.expander("💳 Gestion des Comptes (Manuel)", expanded=False):
                st.info("Ajoutez ou supprimez des comptes qui n'ont pas d'import CSV.")
                
                # --- AJOUTER ---
                n_compte_nom = st.text_input("Nom du compte à créer", placeholder="Ex: Coffre-fort, Prêt Immo", key="input_new_cpte_unique")
                if st.button("➕ Créer le compte", use_container_width=True):
                    if n_compte_nom:
                        if n_compte_nom not in st.session_state.config_groupes:
                            st.session_state.config_groupes[n_compte_nom] = {"Groupe": st.session_state.groupes_liste[0], "Objectif": 0.0, "Solde": 0.0}
                            sauvegarder_config(st.session_state.config_groupes)
                            st.toast(f"Compte '{n_compte_nom}' créé !")
                            st.rerun()
                
                st.divider()

                # --- SUPPRIMER ---
                # On liste les comptes qui existent dans la config
                comptes_existants = list(st.session_state.config_groupes.keys())
                cpte_a_suppr = st.selectbox("Sélectionnez un compte à supprimer", [""] + comptes_existants, key="del_cpte_select")
                
                if st.button("🗑️ Supprimer le compte", use_container_width=True, type="secondary"):
                    if cpte_a_suppr and cpte_a_suppr != "":
                        del st.session_state.config_groupes[cpte_a_suppr]
                        sauvegarder_config(st.session_state.config_groupes)
                        st.warning(f"Compte '{cpte_a_suppr}' supprimé.")
                        st.rerun()
                    else:
                        st.error("Veuillez sélectionner un compte valide.")

        st.markdown("<br>", unsafe_allow_html=True)

        # --- SECTION 2 : CONFIGURATION GÉNÉRALE (LA GRILLE) ---
        st.markdown("### ⚙️ Configuration des soldes et objectifs")
        
        comptes_csv = df_h["Compte"].unique().tolist() if not df_h.empty else []
        comptes_config = list(st.session_state.config_groupes.keys())
        tous_les_comptes = sorted(list(set(comptes_csv + comptes_config)))

        if not tous_les_comptes:
            st.info("Démarrer par importer un fichier ou créer un compte manuel.")
        else:
            # En-têtes de colonnes propres
            h1, h2, h3, h4 = st.columns([2, 2, 1.5, 1.5])
            h1.caption("NOM DU COMPTE")
            h2.caption("GROUPE ASSIGNÉ")
            h3.caption("SOLDE INITIAL")
            h4.caption("OBJECTIF")

            with st.form("form_objectifs_final", border=False):
                for cpte in tous_les_comptes:
                    # Style de la ligne
                    with st.container():
                        old_val = st.session_state.config_groupes.get(cpte, {"Groupe": st.session_state.groupes_liste[0], "Objectif": 0.0, "Solde": 0.0})
                        try:
                            idx = st.session_state.groupes_liste.index(old_val.get("Groupe"))
                        except:
                            idx = 0

                        c1, c2, c3, c4 = st.columns([2, 2, 1.5, 1.5])
                        
                        with c1:
                            badge = "🔘" if cpte in comptes_csv else "⌨️"
                            st.markdown(f"**{badge} {cpte}**")
                        
                        with c2:
                            n_grp = st.selectbox(f"G_{cpte}", st.session_state.groupes_liste, index=idx, key=f"f_grp_{cpte}", label_visibility="collapsed")
                        
                        with c3:
                            n_solde = st.number_input(f"S_{cpte}", value=float(old_val.get("Solde", 0.0)), key=f"f_solde_{cpte}", label_visibility="collapsed", step=100.0)
                        
                        with c4:
                            n_obj = st.number_input(f"O_{cpte}", value=float(old_val.get("Objectif", 0.0)), key=f"f_obj_{cpte}", label_visibility="collapsed", step=100.0)
                        
                        # Mise à jour silencieuse dans le dictionnaire
                        st.session_state.config_groupes[cpte] = {"Groupe": n_grp, "Objectif": n_obj, "Solde": n_solde}
                        st.markdown('<hr style="margin: 5px 0; border:0; border-top:1px solid rgba(128,128,128,0.1);">', unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)
                if st.form_submit_button("💾 Enregistrer toutes les modifications", use_container_width=True, type="primary"):
                    sauvegarder_config(st.session_state.config_groupes)
                    st.success("Configuration sauvegardée avec succès !")
                    time.sleep(1)
                    st.rerun()
  


elif selected == "Gestion":
    # --- TAB GESTION (VERSION CORRIGÉE) ---
        if not df_h.empty:
            # 1. INITIALISATION DES ÉTATS
            for key, val in {
                'filter_g': "Tous", 'filter_c': "Tous", 
                'filter_a': "Toutes", 'filter_m': "Tous", 
                'input_new_cat': ""
            }.items():
                if key not in st.session_state: st.session_state[key] = val

            # 2. PRÉPARATION ET FILTRAGE (Indispensable de le faire ici pour le compteur)
            df_edit = df_h.copy().reset_index(drop=True)
            df_edit['Année'] = df_edit['Date'].dt.year.fillna(0).astype(int)
            
            # Application des filtres successifs
            df_f = df_edit.copy()
            
            if st.session_state.filter_g != "Tous":
                cps = [c for c,v in st.session_state.config_groupes.items() if v["Groupe"] == st.session_state.filter_g]
                df_f = df_f[df_f["Compte"].isin(cps)]
            
            if st.session_state.filter_c != "Tous": 
                df_f = df_f[df_f["Compte"] == st.session_state.filter_c]
                
            if st.session_state.filter_a != "Toutes": 
                df_f = df_f[df_f["Année"] == int(st.session_state.filter_a)]
                
            if st.session_state.filter_m != "Tous": 
                df_f = df_f[df_f["Mois"] == st.session_state.filter_m]

            # 3. MISE EN PAGE : DEUX COLONNES
            col_sidebar, col_main = st.columns([1, 2.5], gap="large")

            # --- COLONNE GAUCHE : OUTILS & FILTRES ---
            with col_sidebar:
                # BLOC AJOUT CATÉGORIE
                st.markdown('<p style="font-weight:bold; color:#7f8c8d; margin-bottom:5px;">✨ Nouvelle catégorie</p>', unsafe_allow_html=True)
                st.markdown("""<style>div[data-testid="stColumn"] button { display: flex; justify-content: center; padding: 5px 0px !important; margin: 0 auto !important; }</style>""", unsafe_allow_html=True)

                with st.container(border=True):
                    emo_vie = ["🐱", "💶", "🅿️", "🍔", "🔧", "🚊", "🎬", "🍴"]
                    emo_fun = ["🧳", "🏦", "🔌", "💧", "👔", "🏠", "🏋️", "🍹"]
                    
                    def display_emoji_row(emoji_list, key_prefix):
                        cols = st.columns(len(emoji_list))
                        for i, e in enumerate(emoji_list):
                            if cols[i].button(e, key=f"{key_prefix}_{i}", use_container_width=True):
                                st.session_state.input_new_cat = e + " "
                                st.rerun()

                    display_emoji_row(emo_vie, "v")
                    display_emoji_row(emo_fun, "f")
                    n_cat = st.text_input("Nom", placeholder="Nom...", label_visibility="collapsed", key="input_new_cat")
                    
                    if st.button("Créer la catégorie ✨", use_container_width=True, type="primary"):
                        if n_cat and len(n_cat.strip()) > 2:
                            sauvegarder_nouvelle_categorie(n_cat)
                            st.toast(f"Ajouté : {n_cat}")
                            st.session_state.input_new_cat = ""
                            st.rerun()

                st.markdown("<br>", unsafe_allow_html=True)

                # BLOC FILTRES
                st.markdown('<p style="font-weight:bold; color:#7f8c8d; margin-bottom:5px;">🔍 Filtres d\'affichage</p>', unsafe_allow_html=True)
                # --- PRÉPARATION DES LISTES ---
                liste_g = ["Tous"] + st.session_state.groupes_liste

                # On s'assure que la valeur sélectionnée existe toujours dans la liste
                idx_g = liste_g.index(st.session_state.filter_g) if st.session_state.filter_g in liste_g else 0

                with st.container(border=True):
                    # 1. Filtre GROUPE
                    new_g = st.selectbox("Groupe", liste_g, index=idx_g)
                    if new_g != st.session_state.filter_g:
                        st.session_state.filter_g = new_g
                        st.session_state.filter_c = "Tous" # On reset le compte si on change de groupe
                        st.rerun()

                    # 2. Filtre COMPTE (dépend du groupe)
                    cps_filtre = ["Tous"] + (comptes_detectes if st.session_state.filter_g == "Tous" else [c for c,v in st.session_state.config_groupes.items() if v["Groupe"] == st.session_state.filter_g])
                    
                    idx_c = cps_filtre.index(st.session_state.filter_c) if st.session_state.filter_c in cps_filtre else 0
                    new_c = st.selectbox("Compte", cps_filtre, index=idx_c)
                    if new_c != st.session_state.filter_c:
                        st.session_state.filter_c = new_c
                        st.rerun()

                    cf1, cf2 = st.columns(2)
                    with cf1:
                        liste_a = ["Toutes"] + sorted(df_edit['Année'].unique().astype(str).tolist(), reverse=True)
                        idx_a = liste_a.index(st.session_state.filter_a) if st.session_state.filter_a in liste_a else 0
                        new_a = st.selectbox("Année", liste_a, index=idx_a)
                        if new_a != st.session_state.filter_a:
                            st.session_state.filter_a = new_a
                            st.rerun()

                    with cf2:
                        liste_m = ["Tous"] + NOMS_MOIS
                        idx_m = liste_m.index(st.session_state.filter_m) if st.session_state.filter_m in liste_m else 0
                        new_m = st.selectbox("Mois", liste_m, index=idx_m)
                        if new_m != st.session_state.filter_m:
                            st.session_state.filter_m = new_m
                            st.rerun()
                            st.markdown("<br>", unsafe_allow_html=True)
                
                # BLOC ACTIONS MASSIVES (Maintenant le compteur sera juste !)
                st.markdown('<p style="font-weight:bold; color:#ff4b4b; margin-bottom:5px;">⚠️ Actions critiques</p>', unsafe_allow_html=True)
                with st.container(border=True):
                    st.caption(f"Cible : {len(df_f)} transactions")
                    if st.button(f"🗑️ Tout supprimer ({len(df_f)})", use_container_width=True, type="secondary"):
                        if not df_f.empty:
                            # On drop les lignes basées sur l'index filtré
                            st.session_state.df = st.session_state.df.drop(df_f.index)
                            st.session_state.df.to_csv("ma_base_de_donnees.csv", index=False, encoding='utf-8-sig')
                            st.toast(f"✅ {len(df_f)} transactions supprimées", icon="🗑️")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.toast("Rien à supprimer", icon="ℹ️")

            # --- COLONNE DROITE : ÉDITION ---
            with col_main:
                df_f['Date_Affiche'] = df_f['Date'].dt.strftime('%d/%m/%Y')
                
                ct1, ct2, ct3 = st.columns([1.5, 1, 0.8]) # On ajoute une 3ème colonne
                with ct1: 
                    st.markdown(f"### 📝 Édition ({len(df_f)})")
                
                with ct2:
                    # On utilise "Categorie" sans accent pour correspondre au DataFrame
                    mode_tri = st.selectbox("📍 Trier par", ["Date", "Montant", "Categorie", "Nom"], label_visibility="collapsed")
                
                with ct3:
                    # Choix de l'ordre
                    ordre = st.selectbox("Ordre", ["Décroissant", "Ascendant"], label_visibility="collapsed")
                    est_ascendant = (ordre == "Ascendant")
                
                # Application du tri
                if mode_tri in df_f.columns:
                    # Cas particulier : pour le montant, on inverse souvent la logique intuitive
                    # (Décroissant = les plus grosses dépenses en premier)
                    df_f = df_f.sort_values(by=mode_tri, ascending=est_ascendant)

                h_col1, h_col2, h_col3, h_col4 = st.columns([3, 2, 2, 0.5])
                h_col1.caption("DÉTAILS")
                h_col2.caption("CATÉGORIE")
                h_col3.caption("MOIS")
                h_col4.caption("X")
        # Conteneur de défilement pour les transactions
                with st.container(height=600, border=True):
                    for idx, row in df_f.iterrows():
                        color_amount = "#2ecc71" if row['Montant'] > 0 else "#ff4b4b"
                        c_info, c_cat, c_mois, c_del = st.columns([3, 2, 2, 0.5])
                        
                        with c_info:
                            st.markdown(f'<div style="border-left:3px solid {color_amount}; padding-left:10px;"><div style="font-weight:bold; font-size:13px;">{row["Nom"]}</div><div style="font-size:11px; color:gray;">{row["Date_Affiche"]} • {row["Compte"]}</div><div style="font-weight:bold; color:{color_amount}; font-size:13px;">{row["Montant"]:.2f} €</div></div>', unsafe_allow_html=True)
                        
                        with c_cat:
                            df_f.at[idx, 'Categorie'] = st.selectbox("C", options=LISTE_CATEGORIES_COMPLETE, index=LISTE_CATEGORIES_COMPLETE.index(row['Categorie']) if row['Categorie'] in LISTE_CATEGORIES_COMPLETE else 0, key=f"cat_{idx}", label_visibility="collapsed")
                        
                        with c_mois:
                            df_f.at[idx, 'Mois'] = st.selectbox("M", options=NOMS_MOIS, index=NOMS_MOIS.index(row['Mois']) if row['Mois'] in NOMS_MOIS else 0, key=f"mo_{idx}", label_visibility="collapsed")
                        
                        with c_del:
                            if st.button("🗑️", key=f"d_{idx}"):
                                st.session_state.df = st.session_state.df.drop(idx)
                                st.session_state.df.to_csv("ma_base_de_donnees.csv", index=False, encoding='utf-8-sig')
                                st.rerun()
                        
                        st.markdown('<hr style="margin:5px 0; border:0; border-top:1px solid rgba(128,128,128,0.05);">', unsafe_allow_html=True)

                # --- ICI ON SORT DE LA BOUCLE FOR (Même niveau que le for) ---
                
                
                # Checkbox hors boucle pour éviter l'erreur DuplicateElementID
                apprendre = st.checkbox(
                    "🧠 Mémoriser les changements de catégories pour les futurs imports", 
                    value=True, 
                    key="global_memo_setting" 
                )

                if st.button("💾 Sauvegarder les modifications", use_container_width=True, type="primary", key="main_save_btn"):
                    if apprendre:
                        for idx_save, row_save in df_f.iterrows():
                            # On compare avec la valeur d'origine dans le session_state
                            ancienne_cat = st.session_state.df.at[idx_save, 'Categorie']
                            nouvelle_cat = row_save['Categorie']
                            if ancienne_cat != nouvelle_cat:
                                sauvegarder_apprentissage(row_save['Nom'], nouvelle_cat)
                    
                    # Mise à jour globale et sauvegarde CSV
                    st.session_state.df.update(df_f)
                    st.session_state.df.to_csv("ma_base_de_donnees.csv", index=False, encoding='utf-8-sig')
                    st.success("Modifications enregistrées ! ✨")
                    time.sleep(1)
                    st.rerun()
                                    
elif selected == "Import":                        
    # --- TAB IMPORT (VERSION CORRIGÉE ET SÉCURISÉE) ---
        st.markdown("""
            <div style="background-color: rgba(255, 255, 255, 0.05); padding: 20px; border-radius: 15px; border: 1px solid rgba(128, 128, 128, 0.1); margin-bottom: 25px;">
                <h2 style="margin: 0; font-size: 24px;">📥 Importation des données</h2>
                <p style="color: gray; font-size: 14px;">Glissez votre relevé bancaire au format CSV pour synchroniser vos comptes.</p>
            </div>
        """, unsafe_allow_html=True)

        col_config, col_upload = st.columns([1, 1.5], gap="large")

        with col_config:
            st.markdown("##### ⚙️ Configuration")
            with st.container(border=True):
                c_mode = st.radio("Type de compte :", ["Existant", "Nouveau"], horizontal=True, label_visibility="collapsed")
                
                if c_mode == "Existant":
                    # --- 1. Comptes issus des transactions ---
                    comptes_transactions = st.session_state.df["Compte"].unique().tolist() if not st.session_state.df.empty else []
                    
                    # --- 2. Comptes issus de la config ---
                    comptes_config = []
                    if os.path.exists("config_comptes.csv"):
                        try:
                            df_cfg = pd.read_csv("config_comptes.csv", encoding='utf-8-sig')
                            # On prend la première colonne (noms des comptes)
                            comptes_config = df_cfg.iloc[:, 0].dropna().unique().tolist()
                        except:
                            pass
                    
                    # --- 3. Fusion sans doublons ---
                    liste_comptes = sorted(list(set(comptes_transactions + comptes_config)))
                    
                    c_nom = st.selectbox("Sélectionner le compte", liste_comptes if liste_comptes else ["Aucun compte"])
                else:
                    c_nom = st.text_input("Nom du nouveau compte", placeholder="ex: Compte Courant Bourso")
                
                st.info("💡 L'algorithme détectera automatiquement les colonnes Date, Nom et Montant.")

        with col_upload:
            st.markdown("##### 📄 Fichier")
            f = st.file_uploader("Glissez le fichier ici", type="csv", key="file_up", label_visibility="collapsed")
            
            if f:
                st.success(f"Fichier détecté : **{f.name}**")
                
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🚀 Lancer l'importation automatique", use_container_width=True, type="primary"):
                if not f:
                    st.error("Veuillez sélectionner un fichier.")
                elif not c_nom or c_nom == "Aucun compte":
                    st.error("Veuillez nommer ou choisir un compte.")
                else:
                    try:
                        with st.spinner("Analyse et catégorisation en cours..."):
                            st.cache_data.clear()
                            raw = f.read()
                            
                            # --- 1. DÉCODAGE ROBUSTE ---
                            text = ""
                            for e in ['latin-1', 'utf-8', 'cp1252', 'utf-8-sig']:
                                try: 
                                    text = raw.decode(e)
                                    break
                                except: continue
                            
                            lines = [l.strip() for l in text.splitlines() if l.strip()]
                            h_idx, sep = None, ','
                            
                            # --- 2. DÉTECTION DE L'EN-TÊTE ---
                            # On cherche la ligne qui contient "Date" ET "Nom" ou "Montant"
                            for i, line in enumerate(lines[:20]):
                                l_lower = line.lower()
                                if "date" in l_lower and (any(m in l_lower for m in ["montant", "debit", "credit", "valeur"])):
                                    h_idx = i
                                    sep = ';' if line.count(';') > line.count(',') else ','
                                    break
                            
                            if h_idx is not None:
                                # --- 3. LECTURE AVEC PARAMÈTRES FORCÉS ---
                                df_n = pd.read_csv(
                                    io.StringIO("\n".join(lines[h_idx:])), 
                                    sep=sep, 
                                    engine='python',
                                    on_bad_lines='skip',
                                    skip_blank_lines=True
                                )
                                
                                # Nettoyage radical des colonnes
                                df_n.columns = [str(c).strip() for c in df_n.columns]
                                df_n = df_n.loc[:, ~df_n.columns.duplicated()].copy()
                                
                                # --- 4. RENOMMAGE ---
                                for std, syns in CORRESPONDANCE.items():
                                    for col in df_n.columns:
                                        if col in syns or col.lower() in [s.lower() for s in syns]: 
                                            df_n = df_n.rename(columns={col: std})
                                
                                # --- 5. VÉRIFICATION ET TRAITEMENT ---
                                cols = df_n.columns.tolist()
                                
                                # On vérifie si on a les données minimales
                                if "Date" in cols:
                                    # Conversion Date
                                    d_col = df_n["Date"].iloc[:, 0] if isinstance(df_n["Date"], pd.DataFrame) else df_n["Date"]
                                    df_n["Date_C"] = pd.to_datetime(d_col.astype(str), dayfirst=True, errors='coerce')
                                    df_n = df_n.dropna(subset=["Date_C"])
                                    
                                    # Détection Montant
                                    if "Debit" in cols and "Credit" in cols:
                                        c1 = df_n["Credit"].apply(clean_montant_physique).fillna(0)
                                        c2 = df_n["Debit"].apply(clean_montant_physique).fillna(0)
                                        df_n["M_Final"] = c1 - c2.abs()
                                    elif "Montant" in cols:
                                        df_n["M_Final"] = df_n["Montant"].apply(clean_montant_physique)
                                    else:
                                        st.error(f"Colonnes trouvées : {cols}. Vérifiez votre fichier CSV.")
                                        st.stop()

                                    # Détection Nom
                                    n_col = "Nom" if "Nom" in cols else (cols[1] if len(cols) > 1 else cols[0])
                                    
                                    # --- 6. CRÉATION DU DF FINAL ---
                                    # --- 6. CRÉATION DU DF FINAL ---
                                    df_res = pd.DataFrame({
                                        "Date": df_n["Date_C"], 
                                        "Nom": df_n[n_col].astype(str).apply(simplifier_nom_definitif),
                                        "Montant": df_n["M_Final"], 
                                        "Compte": [c_nom] * len(df_n)
                                    })

                                    # --- MODIFICATION ICI : On utilise df_n pour avoir accès à TOUTES les colonnes ---
                                    df_res["Categorie"] = df_n.apply(
                                        lambda row: categoriser(row[n_col], row["M_Final"], c_nom, row), 
                                        axis=1
                                    )

                                    df_res["Mois"] = df_res["Date"].dt.month.map(lambda x: NOMS_MOIS[int(x)-1])
                                    df_res["Année"] = df_res["Date"].dt.year
                                    
                                    # --- SAUVEGARDE ET SYNCHRONISATION ---
                                    sauvegarder_donnees(df_res)
                                    
                                    # On recharge TOUTES les données pour mettre à jour la session
                                    if os.path.exists("ma_base_de_donnees.csv"):
                                        # On réutilise ta fonction charger_donnees() définie plus haut pour plus de cohérence
                                        st.session_state.df = charger_donnees()
                                    
                                    st.toast("✅ Données synchronisées !", icon="🚀")
                                    time.sleep(1)
                                    st.rerun()
                                    
                                else:
                                    st.error(f"Structure non reconnue. Colonnes lues : {cols}")
                            else:
                                st.error("Impossible de trouver la ligne d'en-tête (Date, Montant...).")

                    except Exception as e:
                        st.error(f"❌ Erreur critique : {e}")
