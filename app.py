import streamlit as st
import json
import os
from datetime import datetime

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Le Api di CONF - Gestione & Vendite",
    page_icon="🐝",
    layout="centered",
    initial_sidebar_state="collapsed"
)

DATA_FILE = "inventario_miele.json"

DEFAULT_DATA = {
    "tipi_miele": ["Acacia", "Millefiori primaverile", "Millefiori estivo", "Castagno", "Castagno 2026", "Tiglio"],
    "formati": ["1 kg", "500 g"],
    "giacenze": {},        # "Tipo - Formato": quantità
    "prezzi": {},          # "Tipo - Formato": prezzo
    "ordini_pendenti": [], # Lista di ordini non ancora consegnati
    "storico_vendite": []  # Lista di ordini consegnati (per le statistiche)
}

def estrai_peso_kg(formato_str):
    """Estrae il peso in Kg da una stringa formato (es. '1 kg' -> 1.0, '500 g' -> 0.5)."""
    f = formato_str.lower().strip()
    try:
        if 'kg' in f:
            return float(f.replace('kg', '').replace(',', '.').strip())
        elif 'g' in f:
            return float(f.replace('g', '').replace(',', '.').strip()) / 1000.0
    except Exception:
        pass
    return 0.5  # valore di fallback se sconosciuto

def carica_dati():
    """Carica i dati dal file JSON e assicura la presenza di tutte le strutture necessarie."""
    if not os.path.exists(DATA_FILE):
        salva_dati(DEFAULT_DATA)
        return DEFAULT_DATA
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            # Garantisce retrocompatibilità con versioni precedenti del file JSON
            if "prezzi" not in data: data["prezzi"] = {}
            if "ordini_pendenti" not in data: data["ordini_pendenti"] = []
            if "storico_vendite" not in data: data["storico_vendite"] = []
            return data
    except Exception:
        return DEFAULT_DATA

def salva_dati(dati):
    """Salva il dizionario dati nel file JSON."""
    with open(DATA_FILE, "w") as f:
        json.dump(dati, f, indent=4)

if 'db' not in st.session_state:
    st.session_state.db = carica_dati()

if 'carrello' not in st.session_state:
    st.session_state.carrello = {}

def aggiorna_db():
    salva_dati(st.session_state.db)

# --- INTERFACCIA UTENTE ---
st.title("🐝 Le Api di CONF")

tab_vendita, tab_ordini, tab_magazzino, tab_stats, tab_impostazioni = st.tabs([
    "🛒 Nuova Prenotazione", 
    "📋 Ordini Pendenti", 
    "🍯 Magazzino", 
    "📊 Statistiche", 
    "⚙️ Impostazioni"
])

# ==========================================
# TAB 1: NUOVA PRENOTAZIONE / VENDITA
# ==========================================
with tab_vendita:
    st.header("Crea Ordine / Prenotazione")
    
    col1, col2 = st.columns(2)
    with col1:
        tipo_sel = st.selectbox("Tipo di Miele", st.session_state.db["tipi_miele"], key="v_tipo")
    with col2:
        formato_sel = st.selectbox("Formato", st.session_state.db["formati"], key="v_formato")
    
    chiave_prodotto = f"{tipo_sel} - {formato_sel}"
    giacenza_attuale = st.session_state.db["giacenze"].get(chiave_prodotto, 0)
    prezzo_attuale = st.session_state.db["prezzi"].get(chiave_prodotto, 0.0)
    
    st.info(f"📦 Disponibili: **{giacenza_attuale}** vasetti | 💶 Prezzo: **{prezzo_attuale:.2f} €**")
    
    qta_da_aggiungere = st.number_input("Quantità vasetti", min_value=1, value=1, step=1, key="v_qta")
    
    if st.button("➕ Aggiungi al carrello", use_container_width=True):
        qta_gia_in_carrello = st.session_state.carrello.get(chiave_prodotto, 0)
        if qta_gia_in_carrello + qta_da_aggiungere > giacenza_attuale:
            st.error("⚠️ Quantità superiore ai vasetti disponibili a scaffale!")
        else:
            st.session_state.carrello[chiave_prodotto] = qta_gia_in_carrello + qta_da_aggiungere
            st.success(f"Aggiunto al carrello: {qta_da_aggiungere}x {chiave_prodotto}")
            st.rerun()

    if st.session_state.carrello:
        st.divider()
        st.subheader("🧾 Dettaglio Carrello")
        
        totale_euro = 0.0
        dettagli_prodotti = []
        
        for prod, qta in list(st.session_state.carrello.items()):
            p_unitario = st.session_state.db["prezzi"].get(prod, 0.0)
            sub_totale = qta * p_unitario
            totale_euro += sub_totale
            
            # Estrazione tipo e formato per le statistiche
            parti = prod.split(" - ")
            tipo_m = parti[0]
            formato_m = parti[1] if len(parti) > 1 else ""
            
            dettagli_prodotti.append({
                "chiave": prod,
                "tipo": tipo_m,
                "formato": formato_m,
                "qta": qta,
                "prezzo_unitario": p_unitario,
                "subtotale": sub_totale
            })
            
            c_testo, c_elimina = st.columns([4, 1])
            with c_testo:
                st.write(f"**{qta}x** {prod} (*{sub_totale:.2f} €*)")
            with c_elimina:
                if st.button("❌", key=f"del_{prod}"):
                    del st.session_state.carrello[prod]
                    st.rerun()
                    
        st.metric(label="TOTALE ORDINE", value=f"{totale_euro:.2f} €")
        
        st.subheader("Dettagli Cliente e Consegna")
        nome_cliente = st.text_input("Nome Cliente / Note (es. Mario Rossi, Zia Maria)", placeholder="E.g. Marco - Consegna sabato")
        
        tipo_consegna = st.radio("Stato iniziale dell'ordine:", [
            "📌 Prenotazione (Da consegnare in seguito)", 
            "✅ Consegna Immediata (Già consegnato e pagato)"
        ])
        
        col_conf, col_ann = st.columns(2)
        with col_conf:
            if st.button("💾 REGISTRA ORDINE", type="primary", use_container_width=True):
                if not nome_cliente.strip():
                    st.warning("⚠️ Inserisci un nome referente o una nota per l'ordine.")
                else:
                    ora_attuale = datetime.now().strftime("%Y-%m-%d %H:%M")
                    mese_attuale = datetime.now().strftime("%Y-%m")
                    
                    # 1. Scala subito le scorte dallo scaffale per evitare vendite doppie!
                    for item in dettagli_prodotti:
                        st.session_state.db["giacenze"][item["chiave"]] -= item["qta"]
                    
                    nuovo_ordine = {
                        "id": len(st.session_state.db["ordini_pendenti"]) + len(st.session_state.db["storico_vendite"]) + 1,
                        "cliente": nome_cliente.strip(),
                        "data_creazione": ora_attuale,
                        "prodotti": dettagli_prodotti,
                        "totale_euro": totale_euro
                    }
                    
                    if "Prenotazione" in tipo_consegna:
                        nuovo_ordine["stato"] = "Da consegnare"
                        st.session_state.db["ordini_pendenti"].append(nuovo_ordine)
                        st.success(f"📌 Ordine registrato per '{nome_cliente}' tra gli Ordini Pendenti. Scorta scalata!")
                    else:
                        nuovo_ordine["stato"] = "Consegnato"
                        nuovo_ordine["data_consegna"] = ora_attuale
                        nuovo_ordine["mese_consegna"] = mese_attuale
                        st.session_state.db["storico_vendite"].append(nuovo_ordine)
                        st.success(f"✅ Vendita immediata registrata e inviata allo Storico per '{nome_cliente}'!")
                        st.balloons()
                    
                    aggiorna_db()
                    st.session_state.carrello = {}
                    st.rerun()
                    
        with col_ann:
            if st.button("🗑️ Svuota Carrello", use_container_width=True):
                st.session_state.carrello = {}
                st.rerun()

# ==========================================
# TAB 2: ORDINI PENDENTI (DA CONSEGNARE)
# ==========================================
with tab_ordini:
    st.header("Ordini da Consegnare")
    
    ordini_pendenti = st.session_state.db.get("ordini_pendenti", [])
    
    if not ordini_pendenti:
        st.info("🎉 Non ci sono ordini in attesa di consegna! Tutto consegnato.")
    else:
        st.write(f"Ci sono **{len(ordini_pendenti)}** ordini in attesa:")
        
        for idx, ordn in enumerate(ordini_pendenti):
            with st.expander(f"👤 {ordn['cliente']} - Totale: {ordn['totale_euro']:.2f} € (del {ordn['data_creazione']})"):
                st.write("**Prodotti prenotati:**")
                for p in ordn["prodotti"]:
                    st.write(f"- {p['qta']}x {p['chiave']} (*{p['subtotale']:.2f} €*)")
                
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    if st.button(f"✅ Segna come CONSEGNATO", key=f"cons_{idx}", type="primary", use_container_width=True):
                        # Sposta negli ordini consegnati
                        ordn["stato"] = "Consegnato"
                        ora_cons = datetime.now().strftime("%Y-%m-%d %H:%M")
                        ordn["data_consegna"] = ora_cons
                        ordn["mese_consegna"] = datetime.now().strftime("%Y-%m")
                        
                        st.session_state.db["storico_vendite"].append(ordn)
                        st.session_state.db["ordini_pendenti"].pop(idx)
                        aggiorna_db()
                        st.success(f"Ordine per {ordn['cliente']} segnato come consegnato!")
                        st.rerun()
                        
                with col_c2:
                    if st.button(f"❌ Annulla Ordine", key=f"ann_{idx}", use_container_width=True):
                        # Ripristina le giacenze a magazzino
                        for p in ordn["prodotti"]:
                            att = st.session_state.db["giacenze"].get(p["chiave"], 0)
                            st.session_state.db["giacenze"][p["chiave"]] = att + p["qta"]
                        
                        st.session_state.db["ordini_pendenti"].pop(idx)
                        aggiorna_db()
                        st.warning(f"Ordine per {ordn['cliente']} annullato. Vasetti rimessi a magazzino.")
                        st.rerun()

# ==========================================
# TAB 3: GESTIONE SCAFFALE & MAGAZZINO
# ==========================================
with tab_magazzino:
    st.header("Aggiungi Invasettamento")
    
    col1, col2 = st.columns(2)
    with col1:
        tipo_add = st.selectbox("Tipo di Miele", st.session_state.db["tipi_miele"], key="add_tipo")
    with col2:
        formato_add = st.selectbox("Formato", st.session_state.db["formati"], key="add_formato")
        
    chiave_add = f"{tipo_add} - {formato_add}"
    prezzo_memorizzato = st.session_state.db["prezzi"].get(chiave_add, 0.0)
    
    col3, col4 = st.columns(2)
    with col3:
        qta_add = st.number_input("Vasetti da aggiungere", min_value=1, value=10, step=1)
    with col4:
        prezzo_add = st.number_input("Prezzo unitario (€)", min_value=0.0, value=float(prezzo_memorizzato), step=0.5, format="%.2f")
    
    if st.button("Salva in Magazzino e Aggiorna Prezzo", type="primary", use_container_width=True):
        attuale = st.session_state.db["giacenze"].get(chiave_add, 0)
        st.session_state.db["giacenze"][chiave_add] = attuale + qta_add
        st.session_state.db["prezzi"][chiave_add] = prezzo_add
        aggiorna_db()
        st.success(f"✅ Aggiunti {qta_add} vasetti di {chiave_add}.")
        st.rerun()

    st.divider()
    st.header("Stato del Magazzino")
    for tipo in st.session_state.db["tipi_miele"]:
        st.subheader(tipo)
        cols = st.columns(len(st.session_state.db["formati"]))
        for idx, formato in enumerate(st.session_state.db["formati"]):
            chiave = f"{tipo} - {formato}"
            qta = st.session_state.db["giacenze"].get(chiave, 0)
            prz = st.session_state.db["prezzi"].get(chiave, 0.0)
            cols[idx].metric(label=f"{formato} ({prz:.2f} €)", value=f"{qta} vasetti")
        st.divider()

    with st.expander("🛠️ Correggi / Modifica manualmente una giacenza (Admin)"):
        c_cor1, c_cor2 = st.columns(2)
        with c_cor1:
            tipo_corr = st.selectbox("Tipo di Miele", st.session_state.db["tipi_miele"], key="corr_tipo")
        with c_cor2:
            formato_corr = st.selectbox("Formato", st.session_state.db["formati"], key="corr_formato")
            
        chiave_corr = f"{tipo_corr} - {formato_corr}"
        giacenza_reale = st.session_state.db["giacenze"].get(chiave_corr, 0)
        nuova_qta_esatta = st.number_input("Imposta quantità esatta a scaffale", min_value=0, value=int(giacenza_reale), step=1)
        
        if st.button("💾 Sovrascrivi Giacenza", use_container_width=True):
            st.session_state.db["giacenze"][chiave_corr] = nuova_qta_esatta
            aggiorna_db()
            st.success(f"✅ Giacenza aggiornata per {chiave_corr}: {nuova_qta_esatta} vasetti.")
            st.rerun()

# ==========================================
# TAB 4: STATISTICHE & STORICO VENDITE
# ==========================================
with tab_stats:
    st.header("📊 Statistiche & Storico Consegne")
    
    storico = st.session_state.db.get("storico_vendite", [])
    
    if not storico:
        st.info("Non ci sono ancora vendite consegnate registrate nello storico.")
    else:
        # Estrazione di tutti i mesi presenti nello storico
        mesi_disponibili = sorted(list(set(ordn.get("mese_consegna", "N/D") for ordn in storico)), reverse=True)
        mesi_opzioni = ["Tutti i mesi"] + mesi_disponibili
        
        mese_selezionato = st.selectbox("🗓️ Filtra per Mese di Consegna", mesi_opzioni)
        
        # Filtro vendite
        if mese_selezionato == "Tutti i mesi":
            vendite_filtrate = storico
        else:
            vendite_filtrate = [o for o in storico if o.get("mese_consegna") == mese_selezionato]
            
        # Calcolo Metriche Principali
        totale_incasso = sum(o["totale_euro"] for o in vendite_filtrate)
        totale_vasetti = 0
        totale_kg_miele = 0.0
        
        kg_per_tipo = {t: 0.0 for t in st.session_state.db["tipi_miele"]}
        vasetti_per_formato = {f: 0 for f in st.session_state.db["formati"]}
        
        for ordn in vendite_filtrate:
            for p in ordn["prodotti"]:
                qta = p["qta"]
                tipo = p["tipo"]
                formato = p["formato"]
                
                totale_vasetti += qta
                peso_unitario_kg = estrai_peso_kg(formato)
                peso_totale_linea = peso_unitario_kg * qta
                totale_kg_miele += peso_totale_linea
                
                if tipo in kg_per_tipo:
                    kg_per_tipo[tipo] += peso_totale_linea
                else:
                    kg_per_tipo[tipo] = peso_totale_linea
                    
                if formato in vasetti_per_formato:
                    vasetti_per_formato[formato] += qta
                else:
                    vasetti_per_formato[formato] = qta

        # Visualizzazione Metriche aggregate
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Incasso Totale", f"{totale_incasso:.2f} €")
        col_m2.metric("Kg Miele Venduti", f"{totale_kg_miele:.1f} kg")
        col_m3.metric("Vasetti Totali", f"{totale_vasetti} st.")
        
        st.divider()
        
        # Grafici e Breakdown
        st.subheader("🍯 Kg Venduti per Tipo di Miele")
        # Mostra solo i mieli con vendite > 0
        kg_filtrati = {k: v for k, v in kg_per_tipo.items() if v > 0}
        if kg_filtrati:
            st.bar_chart(kg_filtrati)
        else:
            st.write("Nessuna vendita registrata per i tipi attuali.")

        st.subheader("📦 Vasetti Venduti per Formato")
        f_filtrati = {k: v for k, v in vasetti_per_formato.items() if v > 0}
        if f_filtrati:
            st.bar_chart(f_filtrati)
        else:
            st.write("Nessun dato sul formato disponibile.")

        st.divider()
        st.subheader("📜 Registro Dettagliato Consegne")
        for ordn in reversed(vendite_filtrate):
            with st.expander(f"✅ {ordn['cliente']} - {ordn['totale_euro']:.2f} € (Consegnato il {ordn.get('data_consegna', 'N/D')})"):
                for p in ordn["prodotti"]:
                    st.write(f"- {p['qta']}x {p['chiave']} (*{p['subtotale']:.2f} €*)")

# ==========================================
# TAB 5: IMPOSTAZIONI
# ==========================================
with tab_impostazioni:
    st.header("Categorie Dinamiche")
    
    st.subheader("Tipi di Miele")
    col_t1, col_t2 = st.columns([3, 1])
    nuovo_tipo = col_t1.text_input("Nuovo tipo (es. Favo, Tarassaco)")
    if col_t2.button("Aggiungi Tipo", use_container_width=True):
        if nuovo_tipo and nuovo_tipo not in st.session_state.db["tipi_miele"]:
            st.session_state.db["tipi_miele"].append(nuovo_tipo)
            aggiorna_db()
            st.rerun()
    st.write("Attuali:", ", ".join(st.session_state.db["tipi_miele"]))
    
    st.divider()
    
    st.subheader("Formati Vasetti")
    col_f1, col_f2 = st.columns([3, 1])
    nuovo_formato = col_f1.text_input("Nuovo formato (es. 250 g, 100 g)")
    if col_f2.button("Aggiungi Formato", use_container_width=True):
        if nuovo_formato and nuovo_formato not in st.session_state.db["formati"]:
            st.session_state.db["formati"].append(nuovo_formato)
            aggiorna_db()
            st.rerun()
    st.write("Attuali:", ", ".join(st.session_state.db["formati"]))
