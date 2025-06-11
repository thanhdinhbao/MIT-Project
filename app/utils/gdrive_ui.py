import streamlit as st
from loguru import logger
from app.services import gdrive

def upload_and_show(file_url: str):
    """
    Uploads the local video file to Google Drive and displays the shareable link.
    """
    try:
        local_path = file_url
        if file_url.startswith("http"):
            st.info("Skipping upload for remote URL")
            return

        # Prepare a container to display logs in the UI
        log_container = st.empty()
        log_messages = []

        def log_receiver(record):
            # Append each log message and update the container
            log_messages.append(record["message"])
            log_container.code("\n".join(log_messages))

        # Add log handler at INFO level
        handler_id = logger.add(log_receiver, level="INFO")

        with st.spinner("Uploading to Google Drive..."):
            link = gdrive.upload_file(local_path)

        st.success("Upload completed!")
        st.markdown(f"[Mở trên Drive]({link})")
        st.stop()

    except FileNotFoundError as e:
        logger.error(f"Drive upload error: {e}")
        st.error("Google Drive credentials file not found. Vui lòng cung cấp credentials.json.")
    except Exception as e:
        logger.error(f"Drive upload error for {file_url}: {e}")
        st.error(f"Upload thất bại: {e}")
    finally:
        # Remove the log handler to avoid duplicate logs on subsequent calls
        try:
            logger.remove(handler_id)
        except Exception:
            pass
