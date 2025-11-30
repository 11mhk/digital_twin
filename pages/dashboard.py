def load_page():
    import streamlit as st
    st.subheader("Dashboard Page")


    st.markdown(
        """
        <div class="page-title-pill">
            🌍 Map · CO₂ Intensity
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.title("Map View")
    st.caption("Interactive spatial view of CO₂ intensity and simulation layers.")
