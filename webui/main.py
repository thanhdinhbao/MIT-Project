import streamlit as st
st.set_page_config(
    page_title="MIT-Project",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Report a bug": "https://github.com/thanhdinhbao",
        "About": "# MIT-Project\nSimply provide a topic or keyword for a video, and it will "
        "automatically generate the video copy, video materials, video subtitles, "
        "and video background music before synthesizing a high-definition short "
        "video.\n\nhttps://github.com/thanhdinhbao/MIT-Project",
    },
)

import os
import os
import platform
import sys
from uuid import uuid4


from loguru import logger
from ffmpeg_settings import add_ffmpeg_settings_to_ui

root_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)
    print("******** sys.path ********")
    print(sys.path)
    print("")

from app.config import config
from app.models.const import FILE_TYPE_IMAGES, FILE_TYPE_VIDEOS
from app.models.schema import (
    MaterialInfo,
    VideoAspect,
    VideoConcatMode,
    VideoParams,
    VideoTransitionMode,
)
from app.services import llm, voice
from app.services import task as tm
from app.utils.gdrive_ui import upload_and_show
from app.utils import utils


hide_streamlit_style = """
<style>#root > div:nth-child(1) > div > div > div > div > section > div {padding-top: 0rem;}</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)
st.title(f"MIT-Project v{config.project_version}")

support_locales = [
    "en-US",
    "vi-VN",
]

font_dir = os.path.join(root_dir, "resource", "fonts")
song_dir = os.path.join(root_dir, "resource", "songs")
i18n_dir = os.path.join(root_dir, "webui", "i18n")
config_file = os.path.join(root_dir, "webui", ".streamlit", "config.toml")
system_locale = utils.get_system_locale()

if "video_subject" not in st.session_state:
    st.session_state["video_subject"] = ""
if "video_script" not in st.session_state:
    st.session_state["video_script"] = ""
if "video_terms" not in st.session_state:
    st.session_state["video_terms"] = ""
if "ui_language" not in st.session_state:
    st.session_state["ui_language"] = config.ui.get("language", system_locale)


def get_all_fonts():
    fonts = []
    for root, dirs, files in os.walk(font_dir):
        for file in files:
            if file.endswith(".ttf") or file.endswith(".ttc"):
                fonts.append(file)
    fonts.sort()
    return fonts


def get_all_songs():
    songs = []
    for root, dirs, files in os.walk(song_dir):
        for file in files:
            if file.endswith(".mp3"):
                songs.append(file)
    return songs


def open_task_folder(task_id):
    try:
        sys = platform.system()
        path = os.path.join(root_dir, "storage", "tasks", task_id)
        if os.path.exists(path):
            if sys == "Windows":
                os.system(f'start "" "{path}"')
            if sys == "Darwin":
                os.system(f'open "{path}"')
    except Exception as e:
        logger.error(e)


def scroll_to_bottom():
    js = """
    <script>
        console.log("scroll_to_bottom");
        function scroll(dummy_var_to_force_repeat_execution){
            var sections = parent.document.querySelectorAll('section.main');
            console.log(sections);
            for(let index = 0; index<sections.length; index++) {
                sections[index].scrollTop = sections[index].scrollHeight;
            }
        }
        scroll(1);
    </script>
    """
    st.components.v1.html(js, height=0, width=0)


def init_log():
    logger.remove()
    _lvl = "DEBUG"

    def format_record(record):
        file_path = record["file"].path
        relative_path = os.path.relpath(file_path, root_dir)
        record["file"].path = f"./{relative_path}"
        record["message"] = record["message"].replace(root_dir, ".")

        _format = (
            "<green>{time:%Y-%m-%d %H:%M:%S}</> | "
            + "<level>{level}</> | "
            + '"{file.path}:{line}":<blue> {function}</> '
            + "- <level>{message}</>"
            + "\n"
        )
        return _format

    logger.add(
        sys.stdout,
        level=_lvl,
        format=format_record,
        colorize=True,
    )


init_log()

locales = utils.load_locales(i18n_dir)


def tr(key):
    loc = locales.get(st.session_state["ui_language"], {})
    return loc.get("Translation", {}).get(key, key)


st.write(tr("Get Help"))

llm_provider = config.app.get("llm_provider", "").lower()

if not config.app.get("hide_config", False):
    with st.expander(tr("Basic Settings"), expanded=False):
        config_panels = st.columns(3)
        left_config_panel = config_panels[0]
        middle_config_panel = config_panels[1]
        right_config_panel = config_panels[2]
        with left_config_panel:
            display_languages = []
            selected_index = 0
            for i, code in enumerate(locales.keys()):
                display_languages.append(f"{code} - {locales[code].get('Language')}")
                if code == st.session_state["ui_language"]:
                    selected_index = i

            selected_language = st.selectbox(
                tr("Language"), options=display_languages, index=selected_index
            )
            if selected_language:
                code = selected_language.split(" - ")[0].strip()
                st.session_state["ui_language"] = code
                config.ui["language"] = code

            hide_log = st.checkbox(
                tr("Hide Log"), value=config.app.get("hide_log", False)
            )
            config.ui["hide_log"] = hide_log

        with middle_config_panel:
            llm_providers = [
                "OpenAI",
                "Moonshot",
                "Azure",
                "Qwen",
                "DeepSeek",
                "Gemini",
                "Ollama",
                "G4f",
                "OneAPI",
                "Cloudflare",
                "ERNIE",
            ]
            saved_llm_provider = config.app.get("llm_provider", "OpenAI").lower()
            saved_llm_provider_index = 0
            for i, provider in enumerate(llm_providers):
                if provider.lower() == saved_llm_provider:
                    saved_llm_provider_index = i
                    break

            llm_provider = st.selectbox(
                tr("LLM Provider"),
                options=llm_providers,
                index=saved_llm_provider_index,
            )
            llm_helper = st.container()
            llm_provider = llm_provider.lower()
            config.app["llm_provider"] = llm_provider

            llm_api_key = config.app.get(f"{llm_provider}_api_key", "")
            llm_secret_key = config.app.get(
                f"{llm_provider}_secret_key", "")
            llm_base_url = config.app.get(f"{llm_provider}_base_url", "")
            llm_model_name = config.app.get(f"{llm_provider}_model_name", "")
            llm_account_id = config.app.get(f"{llm_provider}_account_id", "")

            tips = ""
            if llm_provider == "ollama":
                if not llm_model_name:
                    llm_model_name = "qwen:7b"
                if not llm_base_url:
                    llm_base_url = "http://localhost:11434/v1"

                with llm_helper:
                    tips = """
                           #####  Cấu hình Ollama
                           - **API Key**: Ví dụ" 123
                           - **Base Url**: http://localhost:11434/v1
                           """

            if llm_provider == "openai":
                if not llm_model_name:
                    llm_model_name = "gpt-3.5-turbo"
                with llm_helper:
                    tips = """
                           ##### Cấu hình OpenAI
                           - **API Key**: [Links](https://platform.openai.com/api-keys)
                           - **Base Url**: Để trống
                           - **Model Name**: [Điền tên mô hình của bạn](https://platform.openai.com/settings/organization/limits)
                           """

            if llm_provider == "moonshot":
                if not llm_model_name:
                    llm_model_name = "moonshot-v1-8k"
                with llm_helper:
                    tips = """
                           ##### Cấu hình Moonshot
                           - **API Key**: [Links](https://platform.moonshot.cn/console/api-keys)
                           - **Base Url**: https://api.moonshot.cn/v1
                           - **Model Name**: [Điền tên mô hình của bạn](https://platform.moonshot.cn/docs/intro#%E6%A8%A1%E5%9E%8B%E5%88%97%E8%A1%A8)
                           """
            if llm_provider == "oneapi":
                if not llm_model_name:
                    llm_model_name = (
                        "claude-3-5-sonnet-20240620"
                    )
                with llm_helper:
                    tips = """
                        ##### Cấu hình OneAPI
                        - **API Key**: Key OneAPI của bạn, [nhấn vào đây để lấy](https://console.oneapi.ai/api-keys)
                        - **Base Url**: URL cơ sở của OneAPI, để trống
                        - **Model Name**: Tên mô hình bạn muốn sử dụng, ví dụ: claude-3-5-sonnet-20240620
                        """

            if llm_provider == "qwen":
                if not llm_model_name:
                    llm_model_name = "qwen-max"
                with llm_helper:
                    tips = """
                           ##### Cấu hình Qwen 
                           - **API Key**: [Nhấp để đăng ký trên trang web chính thức](https://dashscope.console.aliyun.com/apiKey)
                           - **Base Url**: Để trống
                           - **Model Name**: Điền tên mô hình bạn muốn sử dụng, ví dụ: qwen-max
                           """

            if llm_provider == "g4f":
                if not llm_model_name:
                    llm_model_name = "gpt-3.5-turbo"
                with llm_helper:
                    tips = """
                           ##### Cấu hình gpt4free
                           > [GitHub](https://github.com/xtekky/gpt4free)
                           - **API Key**: Điền mã API của bạn, nếu không có thì để trống
                           - **Base Url**: Để trống
                           - **Model Name**: Điền tên mô hình bạn muốn sử dụng, ví dụ: gpt-3.5-turbo
                           """
            if llm_provider == "azure":
                with llm_helper:
                    tips = """
                           ##### Cấu hình Azure
                           > [Hướng dẫn](https://learn.microsoft.com/zh-cn/azure/ai-services/openai/how-to/create-resource)
                           - **API Key**: [Links](https://portal.azure.com/#view/Microsoft_Azure_ProjectOxford/CognitiveServicesHub/~/OpenAI)
                           - **Base Url**: Để trống
                           - **Model Name**: Điền tên mô hình bạn muốn sử dụng, ví dụ: gpt-35-turbo
                           """

            if llm_provider == "gemini":
                if not llm_model_name:
                    llm_model_name = "gemini-1.0-pro"

                with llm_helper:
                    tips = """
                            ##### Cấu hình Gemini
                            
                           - **API Key**: [Links](https://ai.google.dev/)
                           - **Base Url**: Để trống
                           - **Model Name**: Điền tên mô hình bạn muốn sử dụng, ví dụ: gemini-1.0-pro
                           """

            if llm_provider == "deepseek":
                if not llm_model_name:
                    llm_model_name = "deepseek-chat"
                if not llm_base_url:
                    llm_base_url = "https://api.deepseek.com"
                with llm_helper:
                    tips = """
                           ##### Cấu hình DeepSeek
                           - **API Key**: [Links](https://platform.deepseek.com/api_keys)
                           - **Base Url**: Sử dụng địa chỉ API của DeepSeek, ví dụ: https://api.deepseek.com
                           - **Model Name**: Điền tên mô hình bạn muốn sử dụng, ví dụ: deepseek-chat
                           """

            if tips and config.ui["language"] == "zh":
                st.warning(
                    "Khuyến nghị nên dùng Gemini vì nó free =))"
                )
                st.info(tips)

            st_llm_api_key = st.text_input(
                tr("API Key"), value=llm_api_key, type="password"
            )
            st_llm_base_url = st.text_input(tr("Base Url"), value=llm_base_url)
            st_llm_model_name = ""
            if llm_provider != "ernie":
                st_llm_model_name = st.text_input(
                    tr("Model Name"),
                    value=llm_model_name,
                    key=f"{llm_provider}_model_name_input",
                )
                if st_llm_model_name:
                    config.app[f"{llm_provider}_model_name"] = st_llm_model_name
            else:
                st_llm_model_name = None

            if st_llm_api_key:
                config.app[f"{llm_provider}_api_key"] = st_llm_api_key
            if st_llm_base_url:
                config.app[f"{llm_provider}_base_url"] = st_llm_base_url
            if st_llm_model_name:
                config.app[f"{llm_provider}_model_name"] = st_llm_model_name
            if llm_provider == "ernie":
                st_llm_secret_key = st.text_input(
                    tr("Secret Key"), value=llm_secret_key, type="password"
                )
                config.app[f"{llm_provider}_secret_key"] = st_llm_secret_key

            if llm_provider == "cloudflare":
                st_llm_account_id = st.text_input(
                    tr("Account ID"), value=llm_account_id
                )
                if st_llm_account_id:
                    config.app[f"{llm_provider}_account_id"] = st_llm_account_id

        with right_config_panel:

            def get_keys_from_config(cfg_key):
                api_keys = config.app.get(cfg_key, [])
                if isinstance(api_keys, str):
                    api_keys = [api_keys]
                api_key = ", ".join(api_keys)
                return api_key

            def save_keys_to_config(cfg_key, value):
                value = value.replace(" ", "")
                if value:
                    config.app[cfg_key] = value.split(",")

            pexels_api_key = get_keys_from_config("pexels_api_keys")
            pexels_api_key = st.text_input(
                tr("Pexels API Key"), value=pexels_api_key, type="password"
            )
            save_keys_to_config("pexels_api_keys", pexels_api_key)

            pixabay_api_key = get_keys_from_config("pixabay_api_keys")
            pixabay_api_key = st.text_input(
                tr("Pixabay API Key"), value=pixabay_api_key, type="password"
            )
            save_keys_to_config("pixabay_api_keys", pixabay_api_key)

            # Add Gemini API Key
            gemini_api_key = config.app.get("gemini_api_key", "")
            gemini_api_key = st.text_input(
                "Gemini API Key", value=gemini_api_key, type="password",
                help="Get your API key from https://ai.google.dev/"
            )
            if gemini_api_key:
                config.app["gemini_api_key"] = gemini_api_key

            # Add FFMPEG settings
            st.markdown("---")
            ffmpeg_settings = add_ffmpeg_settings_to_ui()

panel = st.columns(3)
left_panel = panel[0]
middle_panel = panel[1]
right_panel = panel[2]

params = VideoParams(video_subject="")
uploaded_files = []

with left_panel:
    with st.container(border=True):
        st.write(tr("Video Script Settings"))
        params.video_subject = st.text_input(
            tr("Video Subject"), value=st.session_state["video_subject"]
        ).strip()

        video_languages = [
            (tr("Auto Detect"), ""),
        ]
        for code in support_locales:
            video_languages.append((code, code))

        selected_index = st.selectbox(
            tr("Script Language"),
            index=0,
            options=range(
                len(video_languages)
            ),  
            format_func=lambda x: video_languages[x][
                0
            ],  
        )
        params.video_language = video_languages[selected_index][1]

        if st.button(
            tr("Generate Video Script and Keywords"), key="auto_generate_script"
        ):
            with st.spinner(tr("Generating Video Script and Keywords")):
                script = llm.generate_script(
                    video_subject=params.video_subject, language=params.video_language
                )
                terms = llm.generate_terms(params.video_subject, script)
                if "Error: " in script:
                    st.error(tr(script))
                elif "Error: " in terms:
                    st.error(tr(terms))
                else:
                    st.session_state["video_script"] = script
                    st.session_state["video_terms"] = ", ".join(terms)
        params.video_script = st.text_area(
            tr("Video Script"), value=st.session_state["video_script"], height=280
        )
        if st.button(tr("Generate Video Keywords"), key="auto_generate_terms"):
            if not params.video_script:
                st.error(tr("Please Enter the Video Subject"))
                st.stop()

            with st.spinner(tr("Generating Video Keywords")):
                terms = llm.generate_terms(params.video_subject, params.video_script)
                if "Error: " in terms:
                    st.error(tr(terms))
                else:
                    st.session_state["video_terms"] = ", ".join(terms)

        params.video_terms = st.text_area(
            tr("Video Keywords"), value=st.session_state["video_terms"]
        )

with middle_panel:
    with st.container(border=True):
        st.write(tr("Video Settings"))
        video_concat_modes = [
            (tr("Sequential"), "sequential"),
            (tr("Random"), "random"),
        ]
        video_sources = [
            (tr("Pexels"), "pexels"),
            (tr("Pixabay"), "pixabay"),
            (tr("Local file"), "local")
        ]

        saved_video_source_name = config.app.get("video_source", "pexels")
        saved_video_source_index = [v[1] for v in video_sources].index(
            saved_video_source_name
        )

        selected_index = st.selectbox(
            tr("Video Source"),
            options=range(len(video_sources)),
            format_func=lambda x: video_sources[x][0],
            index=saved_video_source_index,
        )
        params.video_source = video_sources[selected_index][1]
        config.app["video_source"] = params.video_source

        if params.video_source == "local":
            _supported_types = FILE_TYPE_VIDEOS + FILE_TYPE_IMAGES
            uploaded_files = st.file_uploader(
                "Upload Local Files",
                type=["mp4", "mov", "avi", "flv", "mkv", "jpg", "jpeg", "png"],
                accept_multiple_files=True,
            )

        selected_index = st.selectbox(
            tr("Video Concat Mode"),
            index=1,
            options=range(
                len(video_concat_modes)
            ),  
            format_func=lambda x: video_concat_modes[x][
                0
            ],  
        )
        params.video_concat_mode = VideoConcatMode(
            video_concat_modes[selected_index][1]
        )

        video_transition_modes = [
            (tr("None"), VideoTransitionMode.none.value),
            (tr("Shuffle"), VideoTransitionMode.shuffle.value),
            (tr("FadeIn"), VideoTransitionMode.fade_in.value),
            (tr("FadeOut"), VideoTransitionMode.fade_out.value),
            (tr("SlideIn"), VideoTransitionMode.slide_in.value),
            (tr("SlideOut"), VideoTransitionMode.slide_out.value),
        ]
        selected_index = st.selectbox(
            tr("Video Transition Mode"),
            options=range(len(video_transition_modes)),
            format_func=lambda x: video_transition_modes[x][0],
            index=0,
        )
        params.video_transition_mode = VideoTransitionMode(
            video_transition_modes[selected_index][1]
        )

        video_aspect_ratios = [
            (tr("Portrait"), VideoAspect.portrait.value),
            (tr("Landscape"), VideoAspect.landscape.value),
        ]
        selected_index = st.selectbox(
            tr("Video Ratio"),
            options=range(
                len(video_aspect_ratios)
            ),  # Use the index as the internal option value
            format_func=lambda x: video_aspect_ratios[x][
                0
            ],  # The label is displayed to the user
        )
        params.video_aspect = VideoAspect(video_aspect_ratios[selected_index][1])

        params.video_clip_duration = st.selectbox(
            tr("Clip Duration"), options=[2, 3, 4, 5, 6, 7, 8, 9, 10], index=1
        )
        params.video_count = st.selectbox(
            tr("Number of Videos Generated Simultaneously"),
            options=[1, 2, 3, 4, 5],
            index=0,
        )
    with st.container(border=True):
        st.write(tr("Audio Settings"))

        # Display available TTS providers
        tts_providers_display = ['OpenAI', 'OpenAI FM', 'Gemini']
        saved_tts_provider = config.app.get("tts_provider", "gemini").lower()
        saved_tts_provider_index = 2  # Default to Gemini

        for i, provider in enumerate(tts_providers_display):
            if provider.lower() == saved_tts_provider:
                saved_tts_provider_index = i
                break

        tts_provider = st.selectbox(
            tr("TTS Provider"),
            options=tts_providers_display,
            index=saved_tts_provider_index,
        )
        tts_provider = tts_provider.lower()
        config.app["tts_provider"] = tts_provider

        # Display provider-specific information and get voices
        if tts_provider == "openai":
            st.info("""
            ##### OpenAI TTS Configuration
            - Available voices: alloy, echo, fable, onyx, nova, shimmer
            - High quality speech synthesis
            """)
            voices = [
                "openai-alloy-Male",
                "openai-echo-Male",
                "openai-fable-Female",
                "openai-onyx-Male",
                "openai-nova-Female",
                "openai-shimmer-Female"
            ]
        elif tts_provider == "openai fm":
            st.info("""
            ##### OpenAI FM TTS Configuration
            - Available voices: alloy, ash, ballad, coral, echo, fable, onyx, nova, sage, shimmer, verse
            - Customize tone below
            """)
            voices = [
                "openai_fm-alloy-Unisex",
                "openai_fm-ash-Unisex",
                "openai_fm-ballad-Unisex",
                "openai_fm-coral-Unisex",
                "openai_fm-echo-Unisex",
                "openai_fm-fable-Unisex",
                "openai_fm-onyx-Unisex",
                "openai_fm-nova-Unisex",
                "openai_fm-sage-Unisex",
                "openai_fm-shimmer-Unisex",
                "openai_fm-verse-Unisex"
            ]
            # Add settings for tone for OpenAI FM
            tone_options = [
                "Calm, encouraging, and articulate",
                "Friendly, clear, and reassuring",
                "Neutral and informative"
            ]
            selected_tone = st.selectbox(
                tr("Tone and Style"),
                options=tone_options,
                index=0,
            )
            config.app["openai_fm_tone"] = selected_tone
        elif tts_provider == "gemini":
            st.info("""
            ##### Gemini TTS Configuration
            - 30+ high-quality voices available
            - Supports multiple languages including Vietnamese
            - Powered by Google's latest TTS technology
            """)
            voices = [
                "gemini-achernar-Unisex",
                "gemini-achird-Unisex",
                "gemini-algenib-Unisex",
                "gemini-algieba-Unisex",
                "gemini-alnilam-Unisex",
                "gemini-aoede-Unisex",
                "gemini-autonoe-Unisex",
                "gemini-callirrhoe-Unisex",
                "gemini-charon-Unisex",
                "gemini-despina-Unisex",
                "gemini-enceladus-Unisex",
                "gemini-erinome-Unisex",
                "gemini-fenrir-Unisex",
                "gemini-gacrux-Unisex",
                "gemini-iapetus-Unisex",
                "gemini-kore-Unisex",
                "gemini-laomedeia-Unisex",
                "gemini-leda-Unisex",
                "gemini-orus-Unisex",
                "gemini-puck-Unisex",
                "gemini-pulcherrima-Unisex",
                "gemini-rasalgethi-Unisex",
                "gemini-sadachbia-Unisex",
                "gemini-sadaltager-Unisex",
                "gemini-schedar-Unisex",
                "gemini-sulafat-Unisex",
                "gemini-umbriel-Unisex",
                "gemini-vindemiatrix-Unisex",
                "gemini-zephyr-Unisex",
                "gemini-zubenelgenubi-Unisex"
            ]
        else:
            # Fallback to all voices
            voices = voice.get_all_voices()

        friendly_names = {
            v: v.replace("Female", tr("Female"))
            .replace("Male", tr("Male"))
            .replace("Neural", "")
            for v in voices
        }
        saved_voice_name = config.ui.get("voice_name", "")
        saved_voice_name_index = 0

        # Set default voice based on provider
        if not saved_voice_name or saved_voice_name not in voices:
            if tts_provider == "gemini":
                saved_voice_name = "gemini-zubenelgenubi-Unisex"
            elif tts_provider == "openai":
                saved_voice_name = "openai-alloy-Male"
            elif tts_provider == "openai fm":
                saved_voice_name = "openai_fm-fable-Unisex"

        if saved_voice_name in friendly_names:
            saved_voice_name_index = list(friendly_names.keys()).index(saved_voice_name)
        else:
            # Try to find a voice that matches the UI language
            for i, v in enumerate(voices):
                if (
                    v.lower().startswith(st.session_state["ui_language"].lower())
                    and "V2" not in v
                ):
                    saved_voice_name_index = i
                    break

        selected_friendly_name = st.selectbox(
            tr("Speech Synthesis"),
            options=list(friendly_names.values()),
            index=saved_voice_name_index,
        )

        voice_name = list(friendly_names.keys())[
            list(friendly_names.values()).index(selected_friendly_name)
        ]
        params.voice_name = voice_name
        config.ui["voice_name"] = voice_name

        if st.button(tr("Play Voice")):
            play_content = params.video_subject
            if not play_content:
                play_content = params.video_script
            if not play_content:
                play_content = tr("Voice Example")
            with st.spinner(tr("Synthesizing Voice")):
                temp_dir = utils.storage_dir("temp", create=True)
                audio_file = os.path.join(temp_dir, f"tmp-voice-{str(uuid4())}.mp3")
                sub_maker = voice.tts(
                    text=play_content,
                    voice_name=voice_name,
                    voice_rate=params.voice_rate,
                    voice_file=audio_file,
                )
                # if the voice file generation failed, try again with a default content.
                if not sub_maker:
                    play_content = "This is a example voice. if you hear this, the voice synthesis failed with the original content."
                    sub_maker = voice.tts(
                        text=play_content,
                        voice_name=voice_name,
                        voice_rate=params.voice_rate,
                        voice_file=audio_file,
                    )

                if sub_maker and os.path.exists(audio_file):
                    st.audio(audio_file, format="audio/mp3", start_time=0)
                    logger.info(f"Voice file created and playable at: {audio_file}")
                    if os.path.exists(audio_file):
                        os.remove(audio_file)

        if voice.is_azure_v2_voice(voice_name):
            saved_azure_speech_region = config.azure.get("speech_region", "")
            saved_azure_speech_key = config.azure.get("speech_key", "")
            azure_speech_region = st.text_input(
                tr("Speech Region"), value=saved_azure_speech_region
            )
            azure_speech_key = st.text_input(
                tr("Speech Key"), value=saved_azure_speech_key, type="password"
            )
            config.azure["speech_region"] = azure_speech_region
            config.azure["speech_key"] = azure_speech_key

        params.voice_volume = st.selectbox(
            tr("Speech Volume"),
            options=[0.6, 0.8, 1.0, 1.2, 1.5, 2.0, 3.0, 4.0, 5.0],
            index=2,
            key="voice_volume_selectbox"
        )

        params.voice_rate = st.selectbox(
            tr("Speech Rate"),
            options=[0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.5, 1.8, 2.0],
            index=2,
            key="voice_rate_selectbox"
        )

        bgm_options = [
            (tr("No Background Music"), ""),
            (tr("Random Background Music"), "random"),
            (tr("Custom Background Music"), "custom"),
        ]
        selected_index = st.selectbox(
            tr("Background Music"),
            index=1,
            options=range(
                len(bgm_options)
            ), 
            format_func=lambda x: bgm_options[x][
                0
            ],  
        )
        params.bgm_type = bgm_options[selected_index][1]

        if params.bgm_type == "custom":
            custom_bgm_file = st.text_input(tr("Custom Background Music File"))
            if custom_bgm_file and os.path.exists(custom_bgm_file):
                params.bgm_file = custom_bgm_file
        params.bgm_volume = st.selectbox(
            tr("Background Music Volume"),
            options=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            index=2,
        )

with right_panel:
    with st.container(border=True):
        st.write(tr("Subtitle Settings"))
        params.subtitle_enabled = st.checkbox(tr("Enable Subtitles"), value=True)
        font_names = get_all_fonts()
        saved_font_name = config.ui.get("font_name", "")
        saved_font_name_index = 0
        if saved_font_name in font_names:
            saved_font_name_index = font_names.index(saved_font_name)
        params.font_name = st.selectbox(
            tr("Font"), font_names, index=saved_font_name_index
        )
        config.ui["font_name"] = params.font_name

        subtitle_positions = [
            (tr("Top"), "top"),
            (tr("Center"), "center"),
            (tr("Bottom"), "bottom"),
            (tr("Custom"), "custom"),
        ]
        selected_index = st.selectbox(
            tr("Position"),
            index=2,
            options=range(len(subtitle_positions)),
            format_func=lambda x: subtitle_positions[x][0],
        )
        params.subtitle_position = subtitle_positions[selected_index][1]

        if params.subtitle_position == "custom":
            custom_position = st.text_input(
                tr("Custom Position (% from top)"), value="70.0"
            )
            try:
                params.custom_position = float(custom_position)
                if params.custom_position < 0 or params.custom_position > 100:
                    st.error(tr("Please enter a value between 0 and 100"))
            except ValueError:
                st.error(tr("Please enter a valid number"))

        font_cols = st.columns([0.3, 0.7])
        with font_cols[0]:
            saved_text_fore_color = config.ui.get("text_fore_color", "#FFFFFF")
            params.text_fore_color = st.color_picker(
                tr("Font Color"), saved_text_fore_color
            )
            config.ui["text_fore_color"] = params.text_fore_color

        with font_cols[1]:
            saved_font_size = config.ui.get("font_size", 60)
            params.font_size = st.slider(tr("Font Size"), 30, 100, saved_font_size)
            config.ui["font_size"] = params.font_size

        stroke_cols = st.columns([0.3, 0.7])
        with stroke_cols[0]:
            params.stroke_color = st.color_picker(tr("Stroke Color"), "#000000")
        with stroke_cols[1]:
            params.stroke_width = st.slider(tr("Stroke Width"), 0.0, 10.0, 1.5)

start_button = st.button(tr("Generate Video"), use_container_width=True, type="primary")
if start_button:
    config.save_config()
    task_id = str(uuid4())
    if not params.video_subject and not params.video_script:
        st.error(tr("Video Script and Subject Cannot Both Be Empty"))
        scroll_to_bottom()
        st.stop()

    if params.video_source not in ["pexels", "pixabay", "local"]:
        st.error(tr("Please Select a Valid Video Source"))
        scroll_to_bottom()
        st.stop()

    if params.video_source == "pexels" and not config.app.get("pexels_api_keys", ""):
        st.error(tr("Please Enter the Pexels API Key"))
        scroll_to_bottom()
        st.stop()

    if params.video_source == "pixabay" and not config.app.get("pixabay_api_keys", ""):
        st.error(tr("Please Enter the Pixabay API Key"))
        scroll_to_bottom()
        st.stop()

    if uploaded_files:
        local_videos_dir = utils.storage_dir("local_videos", create=True)
        for file in uploaded_files:
            file_path = os.path.join(local_videos_dir, f"{file.file_id}_{file.name}")
            with open(file_path, "wb") as f:
                f.write(file.getbuffer())
                m = MaterialInfo()
                m.provider = "local"
                m.url = file_path
                if not params.video_materials:
                    params.video_materials = []
                params.video_materials.append(m)

    log_container = st.empty()
    log_records = []

    def log_received(msg):
        if config.ui["hide_log"]:
            return
        with log_container:
            log_records.append(msg)
            st.code("\n".join(log_records))

    logger.add(log_received)

    st.toast(tr("Generating Video"))
    logger.info(tr("Start Generating Video"))
    logger.info(utils.to_json(params))
    scroll_to_bottom()

    result = tm.start(task_id=task_id, params=params)
    if not result or "videos" not in result:
        st.error(tr("Video Generation Failed"))
        logger.error(tr("Video Generation Failed"))
        scroll_to_bottom()
        st.stop()

    video_files = result.get("videos", [])
    st.success(tr("Video Generation Completed"))
    if video_files:
        for i, url in enumerate(video_files):
            with st.container():
                st.video(url)
                if st.button("Upload lên Drive", key=f"upload_{i}"):
                    upload_and_show(url)

    open_task_folder(task_id)
    logger.info(tr("Video Generation Completed"))
    scroll_to_bottom()

config.save_config()
