import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import datetime

# Actualizar la aplicación cada 5 minutos (300,000 milisegundos)
count = st_autorefresh(interval=300000, key="datarefresh")


# Configuración de la página
st.set_page_config(page_title="Dashboard MTTR Maintenance", layout="wide")

st.title("Indicadores Mantenimiento - ABTeflu Norte")

# 1. Reemplaza este enlace con tu URL de Google Sheets (formato CSV)
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQByV1gCIP5jr_Eq7sabppAGWwimkmf8sBhRkW3cdP9b4UV_CsXurM7dA8RKgbred24EGQsg9o8_FzT/pub?gid=0&single=true&output=csv"
SHEET_MAQUINAS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQByV1gCIP5jr_Eq7sabppAGWwimkmf8sBhRkW3cdP9b4UV_CsXurM7dA8RKgbred24EGQsg9o8_FzT/pub?gid=1778461736&single=true&output=csv"

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
    data_maquinas = pd.read_csv(SHEET_MAQUINAS)

    # --- FILTROS EN BARRA LATERAL ---
    st.sidebar.header("Filtros")
    maquinas = st.sidebar.multiselect("Selecciona Máquina(s):", 
                                      options=data["Maquina"].unique(), 
                                      default=data["Maquina"].unique())

    date_filter = st.date_input(
        'Seleccionar un rango de fecha:',
        value=(),
        min_value=None,
        max_value=None,
        format="DD-MM-YYYY")
    
    if (date_filter == ()):
        df_filtered = data[data["Maquina"].isin(maquinas)]
        df_filtered = df_filtered[(df_filtered["Estatus"] == "Cerrada") & (df_filtered["CausoParo"] == "Si")]
    else:
        df_filtered = data[data["Maquina"].isin(maquinas)]
        df_filtered = df_filtered[(df_filtered["Estatus"] == "Cerrada") & (df_filtered["CausoParo"] == "Si") & (df_filtered['FechaInicio'] >= date_filter[1] & (df_filtered['FechaFin'] <= date_filter[2]]]


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

        fig.add_hline(y=meta_mttr, line_dash="dash", line_color="green", annotation_text="Meta MTTR")
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

    

    #st.write(df_pareto_filtered)

    with col5:

        df_pareto = df_filtered[['Maquina','Falla','Duration_Hrs']]
        lista_maquinas = data_maquinas[['ID']]
        #lista_maquinas = lista_maquinas['Maquina'].unique()
        #st.write(lista_maquinas)
        maquina_pareto = st.selectbox(
            "Seleccionar Máquina", options = lista_maquinas)
    
        df_pareto_filtered = df_pareto[df_pareto['Maquina'] == maquina_pareto]
        df_pareto_filtered = df_pareto_filtered.groupby('Falla')['Duration_Hrs'].sum().sort_values(ascending=False).reset_index()
        df_pareto_filtered['PorcentajeAcum'] = df_pareto_filtered['Duration_Hrs'].cumsum()/df_pareto_filtered['Duration_Hrs'].sum()*100
        
        st.subheader("Diagrama de pareto 80-20")
        #fig3 = px.bar(df_pareto_filtered,
                      #x='Falla',
                      #y='Duration_Hrs',
                      #text_auto='.2f',
                      #color='Duration_Hrs',
                      #color_continuous_scale='Reds',
        #              labels={'Duration_Hrs':'Tiempo muerto','Falla':'Clave de Falla'}
        #             )

        #fig3.add_trace(go.Scatter(
        #    x=df_pareto_filtered['Falla'],
        #    y=df_pareto_filtered['PorcentajeAcum']
        #))

        #fig3.update_layout(
        #    yaxis2=dict(title='Porcentaje Acumulado', overlaying='y', side='right', range=[0, 105])
        #)
        
        #st.plotly_chart(fig3, use_container_width=True)
        fig3 = go.Figure()
        
        # Añadir Barras (Eje Y primario)
        fig3.add_trace(
            go.Bar(
                x=df_pareto_filtered['Falla'],
                y=df_pareto_filtered['Duration_Hrs'],
                name='Duración (Hrs)',
                marker=dict(
                    color=df_pareto_filtered['Duration_Hrs'],
                    colorscale='Reds',
                    showscale=False
                )
            )
        )
        
        # Añadir Línea de Porcentaje (Eje Y secundario)
        fig3.add_trace(
            go.Scatter(
                x=df_pareto_filtered['Falla'],
                y=df_pareto_filtered['PorcentajeAcum'],
                name='Porcentaje Acumulado',
                mode='lines+markers',
                line=dict(color='#EF553B', width=3),
                yaxis='y2' # Indicamos que use el segundo eje
            )
        )
        
        # 3. Configuración del Layout para el eje secundario
        fig3.update_layout(
            title='Análisis de Fallas (Pareto)',
            xaxis=dict(title='Falla'),
            yaxis=dict(
                title='Duración (Hrs)',
                side='left'
            ),
            yaxis2=dict(
                title='Porcentaje Acumulado (%)',
                side='right',
                overlaying='y',
                range=[0, 105], # Rango de 0 a 100%
                ticksuffix='%'
            ),
            legend=dict(x=0.8, y=1.1, orientation='h'),
            template='plotly_dark' # Estilo oscuro para que combine con tu imagen
        )
        
        # 4. Mostrar en Streamlit
        #st.title("80-20 Máquina")
        st.plotly_chart(fig3, use_container_width=True)

    #with col6:
    #    st.subheader('Datos')
    #    st.dataframe(df_pareto_filtered, use_container_width=True)
        

    # --- TABLA DE DATOS ---
    with st.expander("Ver datos completos"):
        st.write(df_filtered)

except Exception as e:
    st.error("Error al cargar los datos. Verifica que el enlace de Google Sheets sea correcto y público.")
    st.info("Asegúrate de haber publicado el archivo como CSV en 'Archivo > Compartir > Publicar en la web'")
