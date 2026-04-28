import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import datetime
from datetime import datetime

# Actualizar la aplicación cada 5 minutos (300,000 milisegundos)
count = st_autorefresh(interval=300000, key="datarefresh")


# Configuración de la página
st.set_page_config(page_title="Dashboard MTTR Maintenance", layout="wide")

st.title("Indicadores Mantenimiento - ABTeflu Norte")

# 1. Reemplaza este enlace con tu URL de Google Sheets (formato CSV)
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQByV1gCIP5jr_Eq7sabppAGWwimkmf8sBhRkW3cdP9b4UV_CsXurM7dA8RKgbred24EGQsg9o8_FzT/pub?output=csv"
SHEET_MAQUINAS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQByV1gCIP5jr_Eq7sabppAGWwimkmf8sBhRkW3cdP9b4UV_CsXurM7dA8RKgbred24EGQsg9o8_FzT/pub?gid=1778461736&single=true&output=csv"
SHEET_PROG = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTZcWohnQO0NgCteRK3yYpxf7uRcOmiN4eoobx-usVbkSG0s8CXcQqtRM55LZY5Ju8qUhp5aDayTvQ1/pub?output=csv"

def load_data(url):
    df = pd.read_csv(url)
    
    # Combinar Fecha y Hora para Inicio y Fin
    df['Start_DT'] = pd.to_datetime((df['FechaInicio'] + ' ' + df['HoraInicio']), format='%d/%m/%Y %H:%M')
    df['End_DT'] = pd.to_datetime((df['FechaFin'] + ' ' + df['HoraFin']), format='%d/%m/%Y %H:%M')

    df['FechaInicio_dt'] = pd.to_datetime(df['FechaInicio'], format = '%d/%m/%Y')
    df['Semana'] = df['FechaInicio_dt'].dt.strftime('%U').astype(int)
    
    # Calcular duración en horas (Tiempo de reparación)
    df['Duration_Hrs'] = (df['End_DT'] - df['Start_DT']).dt.total_seconds() / 3600
    
    return df

try:
    data = load_data(SHEET_URL)
    data_maquinas = pd.read_csv(SHEET_MAQUINAS)
    data_prog = pd.read_csv(SHEET_PROG)

    data_prog['Fecha_dt'] = pd.to_datetime(data_prog['Fecha'], format = '%d/%m/%Y')
    data_prog['Semana'] = data_prog['Fecha_dt'].dt.strftime('%U').astype(int)

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
        format="DD/MM/YYYY")

    if (len(date_filter) == 2):
        date_max = data_prog['Fecha_dt'].dt.date.max()
        df_filtered = data[data["Maquina"].isin(maquinas)]
        df_filtered_week = df_filtered[(df_filtered["Estatus"] == "Cerrada") & (df_filtered["CausoParo"] == "Si")]
        df_filtered = df_filtered[(df_filtered["Estatus"] == "Cerrada") & (df_filtered["CausoParo"] == "Si") & (df_filtered['FechaInicio_dt'].dt.date >= date_filter[0]) & (df_filtered['FechaInicio_dt'].dt.date <= date_filter[1])]
        df_filtered_mtbf  = df_filtered[(df_filtered["Estatus"] == "Cerrada") & (df_filtered["CausoParo"] == "Si") & (df_filtered['FechaInicio_dt'].dt.date >= date_filter[0]) & (df_filtered['FechaInicio_dt'].dt.date <= date_max)]
        mtbf_df = data_prog[(data_prog['Fecha_dt'].dt.date >= date_filter[0]) & (data_prog['Fecha_dt'].dt.date <= date_filter[1])]
        mtbf_df = mtbf_df.groupby('Maquina')['minProg'].sum()
        
        
    else:
        df_filtered = data[data["Maquina"].isin(maquinas)]
        df_filtered_week = df_filtered[(df_filtered["Estatus"] == "Cerrada") & (df_filtered["CausoParo"] == "Si")]
        df_filtered = df_filtered[(df_filtered["Estatus"] == "Cerrada") & (df_filtered["CausoParo"] == "Si")]
        date_max = data_prog['Fecha_dt'].dt.date.max()
        date_min = data_prog['Fecha_dt'].dt.date.min()
        df_filtered_mtbf = df_filtered[(df_filtered["Estatus"] == "Cerrada") & (df_filtered["CausoParo"] == "Si") & (df_filtered['FechaInicio_dt'].dt.date >= date_min) & (df_filtered['FechaInicio_dt'].dt.date <= date_max)]
        mtbf_df = data_prog.groupby('Maquina')['minProg'].sum()

    criticas = ['CL-001','CL-003','CL-004','CL-005','CL-007','CL-009','CL-010','C-123','D-228','D-229','D-232','D-233','D-236','CM-007']
    df_week_mtbf = data_prog.groupby('Semana')['minProg'].sum()
    
    # --- CÁLCULO DE MTTR ---

    crit_filtred = st.toggle('Ver Máquinas Principales')

    if crit_filtred:
        df_filtered = df_filtered[df_filtered["Maquina"].isin(criticas)]
        df_filtered_week = df_filtered_week[df_filtered_week["Maquina"].isin(criticas)]
        mttr_df = df_filtered.groupby("Maquina")["Duration_Hrs"].agg(['mean', 'count', 'sum']).reset_index()
        mttr_df.columns = ["Maquina", "MTTR (Horas)", "Cantidad_Fallas",'Tiempo Muerto']
        mttr_df = mttr_df.sort_values(by="MTTR (Horas)", ascending=False)
        mtbf_df_2 = df_filtered_mtbf.groupby('Maquina')['Duration_Hrs'].agg(['sum','count']).reset_index()
        mtbf_df_2.columns = ['Maquina','Tiempo muerto','CantidadFallas']
        mtbf_df_end = pd.merge(mtbf_df, mtbf_df_2, on = 'Maquina', how = 'left')
        total_programado = mtbf_df_end['minProg'].sum()
        total_tm = mtbf_df_end['Tiempo muerto'].sum()
        total_fallas = mtbf_df_end['CantidadFallas'].sum()
        mtbf_df_end = mtbf_df_end.dropna(subset=['CantidadFallas'])
        mtbf_df_end['MTBF (Horas)'] = ((mtbf_df_end['minProg']/60) - (mtbf_df_end['Tiempo muerto'])) / mtbf_df_end['CantidadFallas']
        mtbf_df_end = mtbf_df_end.sort_values(by='MTBF (Horas)', ascending =True)
        df_week = df_filtered_week.groupby('Semana')['Duration_Hrs'].agg(['mean','count','sum']).reset_index()
        df_week.columns = ['Semana','MTTR','CantidadFallas','Downtime']
        df_week_end = pd.merge(df_week, df_week_mtbf, on = 'Semana', how = 'left')
    else:
        df_filtered_week = df_filtered_week[df_filtered_week["Maquina"].isin(criticas)]
        mttr_df = df_filtered.groupby("Maquina")["Duration_Hrs"].agg(['mean', 'count']).reset_index()
        mttr_df.columns = ["Maquina", "MTTR (Horas)", "Cantidad_Fallas"]
        mttr_df = mttr_df.sort_values(by="MTTR (Horas)", ascending=False)
        mtbf_df_2 = df_filtered_mtbf.groupby('Maquina')['Duration_Hrs'].agg(['sum','count']).reset_index()
        mtbf_df_2.columns = ['Maquina','Tiempo muerto','CantidadFallas']
        mtbf_df_end = pd.merge(mtbf_df, mtbf_df_2, on = 'Maquina', how = 'left')
        total_programado = mtbf_df_end['minProg'].sum()
        total_tm = mtbf_df_end['Tiempo muerto'].sum()
        total_fallas = mtbf_df_end['CantidadFallas'].sum()
        mtbf_df_end = mtbf_df_end.dropna(subset=['CantidadFallas'])
        mtbf_df_end['MTBF (Horas)'] = ((mtbf_df_end['minProg']/60) - (mtbf_df_end['Tiempo muerto'])) / mtbf_df_end['CantidadFallas']
        mtbf_df_end = mtbf_df_end.sort_values(by='MTBF (Horas)', ascending =True)
        df_week = df_filtered_week.groupby('Semana')['Duration_Hrs'].agg(['mean','count','sum']).reset_index()
        df_week.columns = ['Semana','MTTR','CantidadFallas','Downtime']
        df_week_end = pd.merge(df_week, df_week_mtbf, on = 'Semana', how = 'left')
    
    # MTTR = Suma de tiempo de reparación / Número de intervenciones
    #mttr_df = df_filtered.groupby("Maquina")["Duration_Hrs"].agg(['mean', 'count']).reset_index()
    #mttr_df.columns = ["Maquina", "MTTR (Horas)", "Cantidad_Fallas"]
    #mttr_df = mttr_df.sort_values(by="MTTR (Horas)", ascending=False)

    # --- VISUALIZACIÓN ---


    col1, col2, col3 = st.columns(3)

    #total_mttr = mttr_df['MTTR (Horas)'].mean()
    total_mttr = df_filtered['Duration_Hrs'].sum()/len(df_filtered)
    meta_mttr = 1.3
    delta_mttr = total_mttr - meta_mttr

    mtbf_global = ((total_programado/60)-total_tm)/total_fallas
    meta_mtbf = 80
    delta_mtbf = mtbf_global - meta_mtbf
    
    with col1:
        st.metric("MTTR Global (Horas)", f"{total_mttr:.2f}", f"{delta_mttr:.2f}", delta_color = "inverse")

    with col2:
        st.metric("Total Intervenciones", len(df_filtered))
    
    col4, col5 = st.columns([2, 1])
    
    with col3:
        st.metric("MTBF Global (Horas)", f"{mtbf_global:.2f}", f"{delta_mtbf:.2f}")


    with col4:
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


    with col5:
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

    #st.write(df_pareto_filtered)

    df_pareto = df_filtered[['Maquina','Falla','Duration_Hrs']]
    lista_maquinas = data_maquinas[['ID']]
    maquina_pareto = st.selectbox(
        "Seleccionar Máquina", options = lista_maquinas)

    col6, col7 = st.columns(2)
    
    with col6:
    
        df_pareto_filtered = df_pareto[df_pareto['Maquina'] == maquina_pareto]
        df_pareto_filtered = df_pareto_filtered.groupby('Falla')['Duration_Hrs'].sum().sort_values(ascending=False).reset_index()
        df_pareto_filtered['PorcentajeAcum'] = df_pareto_filtered['Duration_Hrs'].cumsum()/df_pareto_filtered['Duration_Hrs'].sum()*100
        
        st.subheader("Diagrama de pareto 80-20")

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
        
        st.plotly_chart(fig3, use_container_width=True)


    with col7:
        #cant_falla_df = df_pareto_filtered.gropupby('Falla')['Falla'].agg(['count'])
        cant_falla_df = df_pareto[df_pareto['Maquina'] == maquina_pareto]
        cant_falla_df = cant_falla_df.groupby('Falla', as_index=False).size()
        cant_falla_df = cant_falla_df.rename(columns={'size':'count'})
        cant_falla_df = cant_falla_df.sort_values(by='count', ascending = False)
        #st.write(cant_falla_df)
        st.subheader('Frecuencia de fallas por Máquina')
        
        fig5 = go.Figure()
        
        # Añadir Barras (Eje Y primario)
        fig5.add_trace(
            go.Bar(
                x=cant_falla_df['Falla'],
                y=cant_falla_df['count'],
                name='Frecuencia de fallas por Máquina',
                marker=dict(
                    color=cant_falla_df['count'],
                    colorscale='Reds',
                    showscale=False
                )
            )
        )

        fig5.update_layout(
            title='Frecuencia de fallas por Máquina',
            xaxis=dict(title='Máquina'),
            yaxis=dict(
                title='Cantidad de fallas',
                side='left'
            )
        )
        st.plotly_chart(fig5, use_container_width=True)
        
    col8, col9 = st.columns(2)

    with col8:
        st.subheader('MTBF por Máquina')
        
        fig4 = go.Figure()
        
        # Añadir Barras (Eje Y primario)
        fig4.add_trace(
            go.Bar(
                x=mtbf_df_end['Maquina'],
                y=mtbf_df_end['MTBF (Horas)'],
                name='MTBF (Horas)',
                text=mtbf_df_end['MTBF (Horas)'],
                textposition='auto',
                texttemplate='%{y:.2f}',
                marker=dict(
                    color=mtbf_df_end['MTBF (Horas)'],
                    colorscale='Reds',
                    showscale=False
                )
            )
        )

        fig4.update_layout(
            title='Tiempo medio entre fallas (Horas)',
            xaxis=dict(title='Máquina'),
            yaxis=dict(
                title='MTBF (Horas)',
                side='left'
            )
        )
        fig4.add_hline(y=meta_mtbf, line_dash="dash", line_color="green", annotation_text="Meta MTBF")
        st.plotly_chart(fig4, use_container_width=True)

    with col9:

        tab1, tab2 = st.tabs(
            ['MTTR', 'MTBF'], default = 'MTTR'
        )

        with tab1:

            options = st.multiselect(
                "Selecciona las semanas a graficar:",
                data['Semana'].unique(),
                default = [max(data['Semana']), max(data['Semana'])-1, max(data['Semana'])-2, max(data['Semana'])-3]
            )
            df_week_end = df_week_end[df_week_end['Semana'].isin(options)]
            
            st.subheader('MTTR por Semana')
    
            fig6 = go.Figure()
            
            # Añadir Barras (Eje Y primario)
            fig6.add_trace(
                go.Bar(
                    x = df_week_end['Semana'],
                    y = df_week_end['MTTR'],
                    name='MTTR (Horas)',
                    text=df_week_end['MTTR'],
                    textposition='auto',
                    texttemplate='%{y:.2f}',
                    marker=dict(
                        color=df_week_end['MTTR'],
                        colorscale='Reds',
                        showscale=False
                    )
                )
            )
    
            fig6.update_layout(
                title='MTTR por semana',
                xaxis=dict(title='Semana'),
                yaxis=dict(
                    title='MTTR (Horas)',
                    side='left'
                )
            )
    
            fig6.add_hline(y=meta_mttr, line_dash="dash", line_color="green", annotation_text="Meta MTTR")
            st.plotly_chart(fig6, use_container_width=True)

        with tab2:
            st.write(df_week_end)
        
    
        

    # --- TABLA DE DATOS ---

    #data_prog = data_prog.groupby(['Maquina','Fecha'])['minProg'].sum()

    
    with st.expander("Ver datos completos"):
        st.write(df_filtered)
        st.write(df_week_mtbf)

except Exception as e:
    st.error("Error al cargar los datos. Verifica que el enlace de Google Sheets sea correcto y público.")
    st.info("Asegúrate de haber publicado el archivo como CSV en 'Archivo > Compartir > Publicar en la web'")
