import streamlit as st
import pandas as pd
import requests
from streamlit.components.v1 import html
import httpx
import plotly.express as px
import extra_streamlit_components as stx
from geopy.geocoders import Nominatim
import time
st.markdown("""
<style>
.block-container {
    padding-top: 0rem;
}
</style>
""", unsafe_allow_html=True)
st.markdown("""
<style>
.stTitle { margin: 10px 0; }
.stMarkdown { margin: 5px 0; }
.stForm { margin: 20px auto; max-width: 300px; }
</style>
""", unsafe_allow_html=True)

st.set_page_config(
    page_title="Product Management System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False


geolocator = Nominatim(user_agent="city_finder")
def verify_city(city,flag=False):
    if flag:
        location = geolocator.geocode(city)
        return [location.latitude,location.longitude]
    try:
        location = geolocator.geocode(city,timeout=10)
        if location is not None:
            return True
        return None
    except:
        return False

@st.cache_data
def validate_city(city):
    return verify_city(city)

@st.cache_data
def get_coordinates(city):
    location = geolocator.geocode(city)
    if location:
        return [location.latitude, location.longitude]
    return None

url = "http://127.0.0.1:8000"
cookie_manager = stx.CookieManager()
token = cookie_manager.get('token')

username = cookie_manager.get('username')
st.header('Product Management System')
tab1, tab2, tab3 = st.tabs(['Home', 'Product Data', 'Charts'])


if token and not st.session_state.get('_logging_out', False):
    st.session_state.logged_in = True
    st.session_state.token = token
    st.session_state.username = username
with tab1:

    if st.session_state.logged_in:
        st.text(f'Hi {st.session_state.username}')
        st.write('Welcome to PMS, where you can manage your inventory')
        if st.button('Logout', key='logout'):
            try:
                cookie_manager.delete("token", key='delete_token')
                cookie_manager.delete("username", key='delete_username')
            except:
                pass

            st.session_state.logged_in = False

            html(
                """
                <script>
                    window.top.location.replace(window.top.location.href);
                </script>
                """,
                height=0,
            )

    else:
        st.markdown("<style>p { text-align: center; margin: 10px 0; }</style>", unsafe_allow_html=True)
        st.write('Please Log in to continue into your console')
        with st.form(key='login',):
            user = st.text_input('Username')
            password = st.text_input('Password')
            submit = st.form_submit_button(label='Login')
            if submit:
                try:
                    resp = requests.post(f'{url}/login',data={'username':user,'password':password})
                    resp.raise_for_status()
                    st.success('Success')
                    st.session_state.username = user
                    st.session_state.token = resp.json()['access_token']
                    cookie_manager.set(
                        "token",
                        st.session_state.token,
                        key='token_cookie',
                        expires_at=None
                    )

                    cookie_manager.set(
                        "username",
                        user,
                        key='username_cookie',
                        expires_at=None
                    )
                    st.session_state.logged_in = True
                    time.sleep(3)
                    st.rerun()

                except requests.exceptions.HTTPError:
                    st.error(resp.json()['detail'])

with tab2:
    if st.session_state.logged_in:
        st.header('Products List')
        with httpx.Client(timeout=10) as client:
            resp = client.get(f'{url}/products', headers = {"Authorization": f"Bearer {st.session_state.token}"})
            if 'button' not in st.session_state:
                st.session_state.button = True
            def on_button():
                st.session_state.button = False
            st.session_state.but = st.button('Save',disabled=st.session_state.button,key='Save')
            if st.button('Refresh',key='Refresh'):
                st.session_state.originalDF = pd.DataFrame(client.get(f'{url}/products', headers = {"Authorization": f"Bearer {st.session_state.token}"}).json())
                st.rerun()
            if 'originalDF' not in st.session_state:
                st.session_state['originalDF'] = pd.DataFrame(resp.json())
            edited = pd.DataFrame(st.data_editor(st.session_state.originalDF,num_rows='dynamic',on_change=on_button))

            if st.session_state.but:
                if edited.isnull().any().any() or (edited == "").any().any():
                    st.warning("Please fill all columns before saving.")
                else:
                    orgDF = st.session_state['originalDF']
                    orgIDs = set(orgDF['id'])
                    editedIDs = set(edited['id'])
                    deletedIDs = orgIDs - editedIDs
                    newIDs = editedIDs - orgIDs
                    commonIDs = orgIDs & editedIDs
                    if edited.isnull().any().any():
                        st.warning("Please fill all columns before saving.")
                        st.session_state.button = True
                    if newIDs :
                        editedDF = edited[edited['id'].isin(newIDs)]
                        try:
                            for _, row in editedDF.iterrows():
                                value = row.to_dict()
                                if validate_city(value['location']):
                                    resp = requests.post(f'{url}/products/',json=value, headers = {"Authorization": f"Bearer {st.session_state.token}"})
                                    if resp.status_code == 200:
                                        st.success('Product Inserted Successfully')
                                    else:
                                        st.toast('Product already exists')
                                else:
                                    st.error('Enter Correct city')
                            st.success('Products saved')
                        except:
                            st.error('Data not inserted')

                    if deletedIDs:
                        editedDF = edited[edited['id'].isin(deletedIDs)]
                        for pid in deletedIDs:
                            resp = requests.delete(f'{url}/products/{pid}', headers = {"Authorization": f"Bearer {st.session_state.token}"})
                            if resp.status_code == 200:
                                st.success(f'Product with ID:{pid} deleted Successfully')
                            else:
                                st.error(f'Product with ID:{pid} not found')
                    if commonIDs:
                        for pid in commonIDs:
                            originalDF = st.session_state.originalDF
                            old = originalDF.loc[
                                originalDF['id'] == pid,
                            ].iloc[0]

                            new = edited.loc[
                                edited['id'] == pid,
                            ].iloc[0]

                            if not old.equals(new):
                                value = new.to_dict()
                                if validate_city(value['location']):
                                    resp = requests.put(f'{url}/products/{pid}',json=value, headers = {"Authorization": f"Bearer {st.session_state.token}"})
                                    if resp.status_code == 200:
                                        st.success(f'Product with ID:{pid} updated Successfully')
                                    else:
                                        st.error(f'Product with ID:{pid} not found')
                                else:
                                    st.error('Enter correct city')
    else:
        st.error('Please Log in')
with tab3:
    if st.session_state.logged_in:
        col1, col2 = st.columns(2)
        col3 = st.columns(1)
        with col1:
            inner1, inner2 = st.columns([0.2,0.8])
            st.info('Total Revenue by Categories')
            data = st.session_state.originalDF
            selects = st.multiselect('Select Categories',data['category'].unique(), default=data['category'].unique())
            temp = data[data['category'].isin(selects)].groupby('category')['price'].sum()
            fig = px.pie(temp,values='price',title='Total Revenue by Categories',names=temp.index)
            st.plotly_chart(fig)
        with col2:
            st.info("Price Distribution by City")
            selected_categories = st.multiselect("Select Categories:",
                                                 options=data['category'].unique(),
                                                 default=data['category'].unique())
            selected_cities = st.multiselect("Select Cities:",
                                             options=data['location'].unique(),
                                             default=data['location'].unique())
            filtered_data = data[
                (data['category'].isin(selected_categories)) &
                (data['location'].isin(selected_cities))
                ]
            fig2 = px.scatter(
                filtered_data,
                x='price',
                y='name',
                color='location',
                size='price',
                hover_data=['category', 'created_date'],
                title='Product Price Distribution by City',
                labels={'price': 'Price ($)', 'name': 'Product Name'}
            )
            st.plotly_chart(fig2)
        st.header('Total revenue by City')
        data = st.session_state.originalDF
        cities = data['location'].unique()
        pinpoint = dict()
        for i in cities:
            pinpoint[i] = get_coordinates(i)
        grpByLocation = data.groupby(['location'])['price'].sum()
        grpByLocation_df = grpByLocation.reset_index()
        grpByLocation_df.columns = ['location', 'total_price']
        combined_df = grpByLocation_df.copy()
        combined_df['coordinates'] = combined_df['location'].map(pinpoint)
        combined_df[['latitude', 'longitude']] = pd.DataFrame(combined_df['coordinates'].tolist(),
                                                              index=combined_df.index)
        map_df = combined_df[['latitude', 'longitude', 'location', 'total_price']]
        fig = px.scatter_map(
            map_df,
            lat="latitude",
            lon="longitude",
            hover_name="location",
            hover_data='total_price'
        )
        fig.update_traces(marker={"size": 20})
        fig.update_layout(height=800)
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.error('Please Log in')
