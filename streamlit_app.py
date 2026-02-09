import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

# Actualizar la aplicación cada 5 minutos (300,000 milisegundos)
count = st_autorefresh(interval=300000, key="datarefresh")


# Configuración de la página
st.set_page_config(page_title="Dashboard MTTR Maintenance", layout="wide")

st.title("📊 Dashboard de Mantenimiento - ABTeflu Norte")

# 1. Reemplaza este enlace con tu URL de Google Sheets (formato CSV)
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQByV1gCIP5jr_Eq7sabppAGWwimkmf8sBhRkW3cdP9b4UV_CsXurM7dA8RKgbred24EGQsg9o8_FzT/pub?gid=0&single=true&output=csv"

def load_data(url):
    df = pd.read_csv(url)
    
    # Combinar Fecha y Hora para Inicio y Fin
    df['Start_DT'] = pd.to_datetime(df['FechaInicio'] + ' ' + df['HoraInicio'], format='%d/%m/%Y %H:%M')
    df['End_DT'] = pd.to_datetime(df['FechaFin'] + ' ' + df['HoraFin'], format='%d/%m/%Y %H:%M')
    
    # Calcular duración en horas (Tiempo de reparación)
    df['Duration_Hrs'] = (df['End_DT'] - df['Start_DT']).dt.total_seconds() / 3600
    
    return df

try:
    data = load_data(SHEET_URL)

    # --- FILTROS EN BARRA LATERAL ---
    st.sidebar.header("Filtros")
    maquinas = st.sidebar.multiselect("Selecciona Máquina(s):", 
                                      options=data["Maquina"].unique(), 
                                      default=data["Maquina"].unique())
    
    df_filtered = data[data["Maquina"].isin(maquinas)]
    df_filtered = df_filtered[(df_filtered["Estatus"] == "Cerrada") & (df_filtered["CausoParo"] == "Si")]

    # --- CÁLCULO DE MTTR ---
    # MTTR = Suma de tiempo de reparación / Número de intervenciones
    mttr_df = df_filtered.groupby("Maquina")["Duration_Hrs"].agg(['mean', 'count']).reset_index()
    mttr_df.columns = ["Maquina", "MTTR (Horas)", "Cantidad_Fallas"]
    mttr_df = mttr_df.sort_values(by="MTTR (Horas)", ascending=False)

    # --- VISUALIZACIÓN ---
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("MTTR por Máquina")
        fig = px.bar(mttr_df, 
                     x="Maquina", 
                     y="MTTR (Horas)", 
                     text_auto='.2f',
                     title="Tiempo Medio de Reparación (Horas)",
                     color="MTTR (Horas)",
                     color_continuous_scale="Reds")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Resumen Métricas")
        total_mttr = df_filtered["Duration_Hrs"].mean()
        st.metric("MTTR Global (Horas)", f"{total_mttr:.2f}")
        st.metric("Total Intervenciones", len(df_filtered))
        
        st.dataframe(mttr_df, hide_index=True)

    # --- TABLA DE DATOS ---
    with st.expander("Ver datos completos"):
        st.write(df_filtered)

except Exception as e:
    st.error("Error al cargar los datos. Verifica que el enlace de Google Sheets sea correcto y público.")
    st.info("Asegúrate de haber publicado el archivo como CSV en 'Archivo > Compartir > Publicar en la web'")
