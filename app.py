import streamlit as st
import json
import os

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Gestione - Le Api di CONF",
    page_icon="🐝",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- GESTIONE DATI (JSON LOCALE) ---
DATA_FILE = "inventario_miele.json"

DEFAULT_DATA = {
    "tipi_miele": ["Acacia", "Millefiori primaverile", "Millefiori estivo", "Castagno", "Castagno 2026", "Tiglio"],
    "formati": ["1 kg", "500 g"],
    "giacenze": {}, # Formato chiave: "Tipo - Formato"
    "prezzi": {}    # Novità: Formato chiave: "Tipo - Formato", Valore: Prezzo in Euro (float)
}

def carica_dati():
    """Carica i dati dal file JSON e assicura la retrocompatibilità."""
    if not os.path.exists(DATA_FILE):
        salva_dati(DEFAULT_DATA)
        return DEFAULT_DATA
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            # Retrocompatibilità: se il JSON vecchio non aveva i 'prezzi', li aggiungiamo
            if "prezzi" not in data:
                data["prezzi"] = {}
            return data
    except Exception:
        return DEFAULT_DATA

def salva_dati(dati):
    """Salva il dizionario dati nel file JSON."""
    with open(DATA_FILE, "w") as f:
        json.dump(dati, f, indent=4)

# Inizializza i dati in session state
if 'db' not in st.session_state:
    st.session_state.db = carica_dati()

# Inizializza il carrello (scontrino) per le vendite multiple
if 'carrello' not in st.session_state:
    st.session_state.carrello = {}

def aggiorna_db():
    salva_dati(st.session_state.db)

# --- INTERFACCIA UTENTE ---
st.title("🐝 Le Api di CONF")

tab_vendita, tab_magazzino, tab_impostazioni = st.tabs(["🛒 Vendita", "🍯 Magazzino", "⚙️ Impostazioni"])

# ==========================================
# SEZIONE 1: VENDITA RAPIDA (CON SCONTRINO)
# ==========================================
with tab_vendita:
    st.header("Nuova Vendita")
    
    # 1. Seleziona il prodotto da aggiungere allo scontrino
    col1, col2 = st.columns(2)
    with col1:
        tipo_sel = st.selectbox("Tipo di Miele", st.session_state.db["tipi_miele"], key="v_tipo")
    with col2:
        formato_sel = st.selectbox("Formato", st.session_state.db["formati"], key="v_formato")
    
    chiave_prodotto = f"{tipo_sel} - {formato_sel}"
    giacenza_attuale = st.session_state.db["giacenze"].get(chiave_prodotto, 0)
    prezzo_attuale = st.session_state.db["prezzi"].get(chiave_prodotto, 0.0)
    
    # Mostra giacenza e prezzo
    st.info(f"📦 A scaffale: **{giacenza_attuale}** vasetti | 💶 Prezzo: **{prezzo_attuale:.2f} €**")
    
    # Input quantità
    qta_da_aggiungere = st.number_input("Quantità", min_value=1, value=1, step=1, key="v_qta")
    
    # Bottone per aggiungere al carrello
    if st.button("➕ Aggiungi allo scontrino", use_container_width=True):
        qta_gia_in_carrello = st.session_state.carrello.get(chiave_prodotto, 0)
        
        if qta_gia_in_carrello + qta_da_aggiungere > giacenza_attuale:
            st.error("⚠️ Non hai abbastanza vasetti a scaffale!")
        elif prezzo_attuale == 0.0:
            st.warning("⚠️ Attenzione: il prezzo di questo prodotto è 0€. Impostalo in Magazzino/Impostazioni.")
            st.session_state.carrello[chiave_prodotto] = qta_gia_in_carrello + qta_da_aggiungere
            st.rerun()
        else:
            st.session_state.carrello[chiave_prodotto] = qta_gia_in_carrello + qta_da_aggiungere
            st.rerun()

    # 2. Mostra lo Scontrino (Carrello) se ci sono prodotti
    if st.session_state.carrello:
        st.divider()
        st.subheader("🧾 Scontrino Attuale")
        
        totale_euro = 0.0
        
        # Elenco dei prodotti nel carrello
        for prod, qta in list(st.session_state.carrello.items()):
            p_unitario = st.session_state.db["prezzi"].get(prod, 0.0)
            sub_totale = qta * p_unitario
            totale_euro += sub_totale
            
            c_testo, c_elimina = st.columns([4, 1])
            with c_testo:
                st.write(f"**{qta}x** {prod} (*{sub_totale:.2f} €*)")
            with c_elimina:
                # Tasto per rimuovere l'elemento dal carrello
                if st.button("❌", key=f"del_{prod}"):
                    del st.session_state.carrello[prod]
                    st.rerun()
                    
        # Totale bello grande
        st.metric(label="TOTALE DA INCASSARE", value=f"{totale_euro:.2f} €")
        
        # Conferma o Annulla
        col_conf, col_ann = st.columns(2)
        with col_conf:
            if st.button("✅ CONFERMA VENDITA", type="primary", use_container_width=True):
                # Sottrae dal magazzino
                for prod, qta in st.session_state.carrello.items():
                    st.session_state.db["giacenze"][prod] -= qta
                aggiorna_db()
                
                # Svuota il carrello e festeggia
                st.session_state.carrello = {}
                st.success("Vendita registrata! Scaffale aggiornato.")
                st.balloons()
                # Il rerun ritarda l'effetto dei balloons, usiamo un trucco visivo
        with col_ann:
            if st.button("🗑️ Annulla", use_container_width=True):
                st.session_state.carrello = {}
                st.rerun()


# ==========================================
# SEZIONE 2: GESTIONE SCAFFALE & PREZZI
# ==========================================
with tab_magazzino:
    st.header("Aggiungi Invasettamento")
    
    # Non usiamo st.form qui perché vogliamo che il prezzo di default si 
    # aggiorni dinamicamente quando cambi la selectbox.
    col1, col2 = st.columns(2)
    with col1:
        tipo_add = st.selectbox("Tipo di Miele", st.session_state.db["tipi_miele"], key="add_tipo")
    with col2:
        formato_add = st.selectbox("Formato", st.session_state.db["formati"], key="add_formato")
        
    chiave_add = f"{tipo_add} - {formato_add}"
    
    # Recupera il prezzo salvato per proporlo di default
    prezzo_memorizzato = st.session_state.db["prezzi"].get(chiave_add, 0.0)
    
    col3, col4 = st.columns(2)
    with col3:
        qta_add = st.number_input("Vasetti da aggiungere", min_value=1, value=10, step=1)
    with col4:
        prezzo_add = st.number_input("Prezzo unitario (€)", min_value=0.0, value=float(prezzo_memorizzato), step=0.5, format="%.2f")
    
    if st.button("Salva in Magazzino e Aggiorna Prezzo", type="primary", use_container_width=True):
        attuale = st.session_state.db["giacenze"].get(chiave_add, 0)
        st.session_state.db["giacenze"][chiave_add] = attuale + qta_add
        st.session_state.db["prezzi"][chiave_add] = prezzo_add # Aggiorna il prezzo!
        aggiorna_db()
        st.success(f"✅ Aggiunti {qta_add} vasetti. Prezzo impostato a {prezzo_add:.2f} €.")
        st.rerun()

    st.divider()
    
    st.header("Stato del Magazzino")
    if not st.session_state.db["giacenze"]:
        st.write("Il magazzino è attualmente vuoto.")
    else:
        for tipo in st.session_state.db["tipi_miele"]:
            st.subheader(tipo)
            cols = st.columns(len(st.session_state.db["formati"]))
            for idx, formato in enumerate(st.session_state.db["formati"]):
                chiave = f"{tipo} - {formato}"
                qta = st.session_state.db["giacenze"].get(chiave, 0)
                prz = st.session_state.db["prezzi"].get(chiave, 0.0)
                # Mostra quantità ed etichetta con il prezzo
                cols[idx].metric(label=f"{formato} ({prz:.2f} €)", value=qta)
            st.divider()

# ==========================================
# SEZIONE 3: IMPOSTAZIONI
# ==========================================
with tab_impostazioni:
    st.header("Categorie Dinamiche")
    
    st.subheader("Tipi di Miele")
    col_t1, col_t2 = st.columns([3, 1])
    nuovo_tipo = col_t1.text_input("Nuovo tipo (es. Favo)")
    if col_t2.button("Aggiungi Tipo", use_container_width=True):
        if nuovo_tipo and nuovo_tipo not in st.session_state.db["tipi_miele"]:
            st.session_state.db["tipi_miele"].append(nuovo_tipo)
            aggiorna_db()
            st.rerun()
    st.write("Attuali:", ", ".join(st.session_state.db["tipi_miele"]))
    
    st.divider()
    
    st.subheader("Formati Vasetti")
    col_f1, col_f2 = st.columns([3, 1])
    nuovo_formato = col_f1.text_input("Nuovo formato (es. 250 g)")
    if col_f2.button("Aggiungi Formato", use_container_width=True):
        if nuovo_formato and nuovo_formato not in st.session_state.db["formati"]:
            st.session_state.db["formati"].append(nuovo_formato)
            aggiorna_db()
            st.rerun()
    st.write("Attuali:", ", ".join(st.session_state.db["formati"]))