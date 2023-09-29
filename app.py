from pathlib import Path
import streamlit as st

from dotenv import load_dotenv

load_dotenv()

@st.cache_resource(show_spinner=False)
def create_agent():
    from src.llm.agent import make_agent
    from src.llm.callback_handler import StreamlitCallbackHandler
    app_handler = StreamlitCallbackHandler()
    return make_agent(callbacks=[app_handler]), app_handler


st.set_page_config(layout='wide')

data_path = Path('data/new/')
files = list(data_path.glob('*.jpg')) + list(data_path.glob('*.png')) + list(data_path.glob('*.jpeg'))
image_files = {}
for file in sorted(files):
    image_files[file.name] = str(file)

col1, col2 = st.columns(2)

with col1:
    selected_image = st.selectbox('Select an image', sorted(image_files.keys()))

    if selected_image:
        st.image(image_files[selected_image])

result = col1.container()

with col2:
    st.header("Event Agent")
    with st.spinner('Loading model...'):
        agent, app_handler = create_agent()

    steps = st.slider('Steps', 1, 10, 6)

    force = st.checkbox('Force run')

    if st.button('Start'):
        pb = st.progress(0, text="Creating event...")
        tabs = st.tabs([f"History {i+1}" for i in range(steps)])
        app_handler.set_app(steps, pb, tabs, result)
        agent.run(image_files[selected_image], steps, force)
