import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

# Actualizar la aplicación cada 5 minutos (300,000 milisegundos)
count = st_autorefresh(interval=300000, key="datarefresh")


# Configuración de la página
st.set_page_config(page_title="Dashboard MTTR Maintenance", layout="wide")

st.title("Indicadores Mantenimiento - ABTeflu Norte")

# 1. Reemplaza este enlace con tu URL de Google Sheets (formato CSV)
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQByV1gCIP5jr_Eq7sabppAGWwimkmf8sBhRkW3cdP9b4UV_CsXurM7dA8RKgbred24EGQsg9o8_FzT/pub?gid=0&single=true&output=csv"

def load_data(url):
    df = pd.read_csv(url)
    
    # Combinar Fecha y Hora para Inicio y Fin
    df['Start_DT'] = pd.to_datetime((df['FechaInicio'] + ' ' + df['HoraInicio']), format='%d/%m/%Y %H:%M')
    df['End_DT'] = pd.to_datetime((df['FechaFin'] + ' ' + df['HoraFin']), format='%d/%m/%Y %H:%M')
    
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


    criticas = ['CL-001','CL-003','CL-005','CL-007','CL-009','CL-010','C-123','D-228','D-229','D-232','D-233','D-236','CM-007','RB-003']
    
    # --- CÁLCULO DE MTTR ---

    crit_filtred = st.toggle('Ver Máquinas Críticas')

    if crit_filtred:
        df_filtered = df_filtered[df_filtered["Maquina"].isin(criticas)]
        mttr_df = df_filtered.groupby("Maquina")["Duration_Hrs"].agg(['mean', 'count']).reset_index()
        mttr_df.columns = ["Maquina", "MTTR (Horas)", "Cantidad_Fallas"]
        mttr_df = mttr_df.sort_values(by="MTTR (Horas)", ascending=False)
    else:
        mttr_df = df_filtered.groupby("Maquina")["Duration_Hrs"].agg(['mean', 'count']).reset_index()
        mttr_df.columns = ["Maquina", "MTTR (Horas)", "Cantidad_Fallas"]
        mttr_df = mttr_df.sort_values(by="MTTR (Horas)", ascending=False)
    
    # MTTR = Suma de tiempo de reparación / Número de intervenciones
    #mttr_df = df_filtered.groupby("Maquina")["Duration_Hrs"].agg(['mean', 'count']).reset_index()
    #mttr_df.columns = ["Maquina", "MTTR (Horas)", "Cantidad_Fallas"]
    #mttr_df = mttr_df.sort_values(by="MTTR (Horas)", ascending=False)

    # --- VISUALIZACIÓN ---


    col1, col2 = st.columns(2)

    total_mttr = df_filtered["Duration_Hrs"].mean()
    meta_mttr = 1.2
    delta_mttr = total_mttr - meta_mttr
    
    with col1:
        st.metric("MTTR Global (Horas)", f"{total_mttr:.2f}", f"{delta_mttr:.2f}", delta_color = "inverse")

    with col2:
        st.metric("Total Intervenciones", len(df_filtered))
    
    col3, col4 = st.columns([2, 1])

    with col3:
        st.subheader("MTTR por Máquina")
        fig = px.bar(mttr_df, 
                     x="Maquina", 
                     y="MTTR (Horas)", 
                     text_auto='.2f',
                     title="Tiempo Medio de Reparación (Horas)",
                     color="MTTR (Horas)",
                     color_continuous_scale="Reds")
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        mttr_df = mttr_df.sort_values(by="Cantidad_Fallas", ascending=True)
        st.subheader("Frecuencia Fallas")
        fig2 = px.bar(mttr_df,
                     x="Cantidad_Fallas",
                     y="Maquina",
                     text_auto='.0f',
                     title="Cantidad de fallas",
                     color="Cantidad_Fallas",
                     color_continuous_scale="Reds",
                     orientation='h')
        st.plotly_chart(fig2, use_container_widht=True)

    col5, col6 = st.columns(2)

    data_8020 = data['Maquina','Falla','Duration_Hrs']
    lista_maquinas = data_8020.sort_values(by="Maquina", ascending = True)
    #lista_maquinas = lista_maquinas['Maquina'].unique()
    st.write(lista_maquinas)
    #maquina_pareto = st.selectbox(
    #    "Seleccionar Máquina", options = lista_maquinas)

    

    #with col5:
        #st.subheader("Diagrama de pareto 80-20")
        #fig3 = px.bar(xxx,
        #              x = "Falla",
        #              y = "Tiempo muerto (horas)",
        

    # --- TABLA DE DATOS ---
    with st.expander("Ver datos completos"):
        st.write(df_filtered)

except Exception as e:
    st.error("Error al cargar los datos. Verifica que el enlace de Google Sheets sea correcto y público.")
    st.info("Asegúrate de haber publicado el archivo como CSV en 'Archivo > Compartir > Publicar en la web'")
