import logging
import json
import io

import pandas as pd

from port.api.commands import (CommandSystemDonate, CommandSystemExit, CommandUIRender)
import port.api.props as props
import port.helpers as helpers
import port.unzipddp as unzipddp
import port.netflix as netflix
import port.experiment as experiment


LOG_STREAM = io.StringIO()

logging.basicConfig(
    stream=LOG_STREAM,
    level=logging.INFO,
    format="%(asctime)s --- %(name)s --- %(levelname)s --- %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S%z",
)

LOGGER = logging.getLogger("script")

TABLE_TITLES = {
    "netflix_ratings": props.Translatable(
        {
            "en": "Ratings you gave according to Netlix:",
            "nl": "Jouw beoordelingen volgens Netflix:",
        }
    ),
}

# Questionnaire questions
UNDERSTANDING = props.Translatable({
    "en": "How would you describe the information that you shared with Utrecht University researchers?",
    "nl": "Open vraag?"
})

INDENTIFY_CONSUMPTION = props.Translatable({"en": "In case you looked at the data presented on this page, did you recognise your Netflix watching patterns?", "nl": "asd"})
IDENTIFY_CONSUMPTION_CHOICES = [
    props.Translatable({"en": "I recognized my Netflix watching patterns", "nl": "asd"}),
    props.Translatable({"en": "I recognized my Netflix watching patterns and patters of those I share my account with", "nl": "asd"}),
    props.Translatable({"en": "I recognized mostly the watching patterns of those I share my account with", "nl": "asd"}),
    props.Translatable({"en": "I did not look at my data ", "nl": "asd"}),
    props.Translatable({"en": "Other", "nl": "asd"})
]

ENJOYMENT = props.Translatable({"en": "In case you looked at the data presented on this page, how interesting did you find looking at your data?", "nl": "asd"})
ENJOYMENT_CHOICES = [
    props.Translatable({"en": "not at all interesting", "nl": "asd"}),
    props.Translatable({"en": "somewhat uninteresting", "nl": "asd"}),
    props.Translatable({"en": "neither interesting nor uninteresting", "nl": "asd"}),
    props.Translatable({"en": "somewhat interesting", "nl": "asd"}),
    props.Translatable({"en": "very interesting", "nl": "asd"})
]

ADDITIONAL_COMMENTS = props.Translatable({
    "en": "Do you have any additional comments about the donation? Please add them here.",
    "nl": "Open vraag?"
})

#Not donate questions
NO_DONATION_REASONS = props.Translatable({
    "en": "What is/are the reason(s) that you decided not to donate your data?",
    "nl": "Open vraag?"
})


def process(session_id):
    LOGGER.info("Starting the donation flow")
    yield donate_logs(f"{session_id}-tracking")

    # progress in %
    subflows = 1
    steps = 3
    step_percentage = (100 / subflows) / steps
    progress = 0
    progress += step_percentage

    platform_name = "Netflix"
    table_list = None
    group_label = "A"

    while True:
        LOGGER.info("Prompt for file for %s", platform_name)
        yield donate_logs(f"{session_id}-tracking")

        promptFile = prompt_file("application/zip, text/plain", platform_name)
        file_result = yield render_donation_page(platform_name, promptFile, progress)
        selected_user = ""

        if file_result.__type__ == "PayloadString":
            validation = netflix.validate_zip(file_result.value)

            # Flow logic
            # Happy flow: Valid DDP, user was set selected
            # Retry flow 1: No user was selected, cause could be for multiple reasons see code
            # Retry flow 2: No valid Netflix DDP was found
            # Retry flows are separated for clarity and you can provide different messages to the user

            if validation.ddp_category is not None:
                LOGGER.info("Payload for %s", platform_name)
                yield donate_logs(f"{session_id}-tracking")

                # Extract the user
                users = extract_users(file_result.value)

                # Experiment logic: you can flip A and B switches to see both conditions with the same DDP
                group_label = experiment.assign_experiment_group("".join(users))
                
                if group_label == "A":
                    extract_netflix = extract_netflix_A
                if group_label == "B":
                    extract_netflix = extract_netflix_B
                else:
                    group_label = "A"
                    extract_netflix = extract_netflix_A

                if len(users) == 1:
                    selected_user = users[0]
                    extraction_result = extract_netflix(file_result.value, selected_user)
                    table_list = extraction_result
                elif len(users) > 1:
                    selection = yield prompt_radio_menu_select_username(users, progress)
                    if selection.__type__ == "PayloadString":
                        selected_user = selection.value
                        extraction_result = extract_netflix(file_result.value, selected_user)
                        table_list = extraction_result
                    else:
                        LOGGER.info("User skipped during user selection")
                        pass
                else:
                    LOGGER.info("No users could be found in DDP")
                    pass

            # Enter retry flow, reason: if DDP was not a Netflix DDP
            if validation.ddp_category is None:
                LOGGER.info("Not a valid %s zip; No payload; prompt retry_confirmation", platform_name)
                yield donate_logs(f"{session_id}-tracking")
                retry_result = yield render_donation_page(platform_name, retry_confirmation(platform_name), progress)

                if retry_result.__type__ == "PayloadTrue":
                    continue
                else:
                    LOGGER.info("Skipped during retry ending flow")
                    yield donate_logs(f"{session_id}-tracking")
                    break

            # Enter retry flow, reason: valid DDP but no users could be extracted
            if selected_user == "":
                LOGGER.info("Selected user is empty after selection, enter retry flow")
                yield donate_logs(f"{session_id}-tracking")
                retry_result = yield render_donation_page(platform_name, retry_confirmation(platform_name), progress)

                if retry_result.__type__ == "PayloadTrue":
                    continue
                else:
                    LOGGER.info("Skipped during retry ending flow")
                    yield donate_logs(f"{session_id}-tracking")
                    break

        else:
            LOGGER.info("Skipped at file selection ending flow")
            yield donate_logs(f"{session_id}-tracking")
            break

        # STEP 2: ask for consent
        progress += step_percentage

        if table_list is not None:
            LOGGER.info("Prompt consent; %s", platform_name)
            yield donate_logs(f"{group_label}-{session_id}-tracking")
            prompt = create_consent_form(table_list)
            consent_result = yield render_donation_page(platform_name, prompt, progress)

            # Data was donated
            if consent_result.__type__ == "PayloadJSON":
                LOGGER.info("Data donated; %s", platform_name)
                yield donate(f"{group_label}-{platform_name}", consent_result.value)
                yield donate_logs(f"{group_label}-{session_id}-tracking")

                progress += step_percentage
                # render happy questionnaire
                render_questionnaire_results = yield render_questionnaire(progress)

                if render_questionnaire_results.__type__ == "PayloadJSON":
                    yield donate(f"{group_label}-questionnaire-donation", render_questionnaire_results.value)
                else:
                    LOGGER.info("Skipped questionnaire: %s", platform_name)
                    yield donate_logs(f"{group_label}-{session_id}-tracking")

            # Data was not donated
            else:
                LOGGER.info("Skipped ater reviewing consent: %s", platform_name)
                yield donate_logs(f"{group_label}-{session_id}-tracking")

                progress += step_percentage

                # render sad questionnaire
                render_questionnaire_results = yield render_questionnaire_no_donation(progress)
                if render_questionnaire_results.__type__ == "PayloadJSON":
                    yield donate(f"{group_label}-questionnaire-no-donation", render_questionnaire_results.value)
                else:
                    LOGGER.info("Skipped questionnaire: %s", platform_name)
                    yield donate_logs(f"{session_id}-tracking")

            break

    yield exit(0, "Success")
    yield render_end_page()


##################################################################

def create_consent_form(table_list: list[props.PropsUIPromptConsentFormTable]) -> props.PropsUIPromptConsentForm:
    """
    Assembles all donated data in consent form to be displayed
    """
    return props.PropsUIPromptConsentForm(table_list, meta_tables=[])


def return_empty_result_set():
    result = {}

    df = pd.DataFrame(["No data found"], columns=["No data found"])
    result["empty"] = {"data": df, "title": TABLE_TITLES["empty_result_set"]}

    return result


def donate_logs(key):
    log_string = LOG_STREAM.getvalue()  # read the log stream
    if log_string:
        log_data = log_string.split("\n")
    else:
        log_data = ["no logs"]

    return donate(key, json.dumps(log_data))


def prompt_radio_menu_select_username(users, progress):
    """
    Prompt selection menu to select which user you are
    """

    title = props.Translatable({ "en": "Select", "nl": "Select" })
    description = props.Translatable({ "en": "Please select your username", "nl": "Selecteer uw gebruikersnaam" })
    header = props.PropsUIHeader(props.Translatable({"en": "Select", "nl": "Select"}))

    radio_items = [{"id": i, "value": username} for i, username in enumerate(users)]
    body = props.PropsUIPromptRadioInput(title, description, radio_items)
    footer = props.PropsUIFooter(progress)

    page = props.PropsUIPageDonation("Netflix", header, body, footer)

    return CommandUIRender(page)


##################################################################
# Extraction function

# The A conditional group gets the visualizations 
def extract_netflix_A(netflix_zip: str, selected_user: str) -> list[props.PropsUIPromptConsentFormTable]:
    """
    Main data extraction function
    Assemble all extraction logic here, results are stored in a dict

    COMMENT: does this also make sense as the place to formulate data visualizations?
    """
    tables_to_render = []
    
    # Extract the ratings
    df = netflix.ratings_to_df(netflix_zip, selected_user)
    if not df.empty:
        table_title = props.Translatable({"en": "Netflix ratings", "nl": "Netflix ratings"})
        table_description = props.Translatable({"en": "We can add a short description here", "nl": "Hier kunnen we een korte beschrijving toevoegen"})
        wordcloud = props.PropsUITextVisualization(
            title=props.Translatable({"en": "Highest ratings", "nl": "Hoogste ratings"}),
            type="wordcloud",
            text_column="Title Name",
            value_column="Thumbs Value",
            value_aggregation="mean"      
        )
        table = props.PropsUIPromptConsentFormTable("netflix_rating", table_title, df, table_description, [wordcloud])
        tables_to_render.append(table)

    # Extract the viewing activity
    df = netflix.viewing_activity_to_df(netflix_zip, selected_user)
    if not df.empty:
        table_title = props.Translatable({"en": "Netflix viewings", "nl": "Netflix viewings"})
        table_description = None

        date_graph = props.PropsUIChartVisualization(
            title=props.Translatable({"en": "Hours Netflix watched", "nl": "Uren Netflix gekeken"}),
            type="area",
            group= props.PropsUIChartGroup(column="Start Time", label='Datum', dateFormat="auto"),
            values= [props.PropsUIChartValue(label='Uren Netflix gekeken', column='Duration in hours', aggregate="sum", addZeroes= True)]
        )
        hour_graph = props.PropsUIChartVisualization(
            title=props.Translatable({"en": "At what time of the day do you watch?", "nl": "Op welk tijdstip van de dag kijk je?"}),
            type="bar",
            group= props.PropsUIChartGroup(column="Start Time", label='Uur van de dag', dateFormat="hour_cycle"),
            values= [props.PropsUIChartValue(label='Aantal uur gekeken', column='Duration in hours', aggregate="sum", addZeroes= True)]
        )
        table = props.PropsUIPromptConsentFormTable("netflix_viewings", table_title, df, table_description, [date_graph, hour_graph]) 
        tables_to_render.append(table)
    
    # Extract the clickstream
    df = netflix.clickstream_to_df(netflix_zip, selected_user)
    if not df.empty:
        table_title = props.Translatable({"en": "Netflix clickstream", "nl": "Netflix clickstream"})
        table = props.PropsUIPromptConsentFormTable("netflix_clickstream", table_title, df) 
        tables_to_render.append(table)

    # Extract my list
    df = netflix.my_list_to_df(netflix_zip, selected_user)
    if not df.empty:
        table_title = props.Translatable({"en": "Netflix bookmarks", "nl": "Netflix bookmarks"})
        table = props.PropsUIPromptConsentFormTable("netflix_my_list", table_title, df) 
        tables_to_render.append(table)

    # Extract Indicated preferences
    df = netflix.indicated_preferences_to_df(netflix_zip, selected_user)
    if not df.empty:
        table_title = props.Translatable({"en": "Netflix indicated preferences", "nl": "Netflix indicated preferences"})
        table = props.PropsUIPromptConsentFormTable("netflix_indicated_preferences", table_title, df) 
        tables_to_render.append(table)

    # Extract playback related events
    df = netflix.playback_related_events_to_df(netflix_zip, selected_user)
    if not df.empty:
        table_title = props.Translatable({"en": "Netflix playback related events", "nl": "Netflix playback related events"})
        table = props.PropsUIPromptConsentFormTable("netflix_playback", table_title, df) 
        tables_to_render.append(table)

    # Extract search history
    df = netflix.search_history_to_df(netflix_zip, selected_user)
    if not df.empty:
        table_title = props.Translatable({"en": "Netflix search history", "nl": "Netflix search history"})
        table = props.PropsUIPromptConsentFormTable("netflix_search", table_title, df) 
        tables_to_render.append(table)

    # Extract messages sent by netflix
    df = netflix.messages_sent_by_netflix_to_df(netflix_zip, selected_user)
    if not df.empty:
        table_title = props.Translatable({"en": "Netflix messages", "nl": "Netflix messages"})
        table = props.PropsUIPromptConsentFormTable("netflix_messages", table_title, df) 
        tables_to_render.append(table)

    return tables_to_render



# The B group does not get the visualizations
def extract_netflix_B(netflix_zip: str, selected_user: str) -> list[props.PropsUIPromptConsentFormTable]:
    """
    Main data extraction function
    Assemble all extraction logic here, results are stored in a dict

    COMMENT: does this also make sense as the place to formulate data visualizations?
    """
    tables_to_render = []
    
    # Extract the ratings
    df = netflix.ratings_to_df(netflix_zip, selected_user)
    if not df.empty:
        table_title = props.Translatable({"en": "Netflix ratings", "nl": "Netflix ratings"})
        table = props.PropsUIPromptConsentFormTable("netflix_rating", table_title, df)
        tables_to_render.append(table)

    # Extract the viewing activity
    df = netflix.viewing_activity_to_df(netflix_zip, selected_user)
    if not df.empty:
        table_title = props.Translatable({"en": "Netflix viewings", "nl": "Netflix viewings"})
        table = props.PropsUIPromptConsentFormTable("netflix_viewings", table_title, df)
        tables_to_render.append(table)
    
    # Extract the clickstream
    df = netflix.clickstream_to_df(netflix_zip, selected_user)
    if not df.empty:
        table_title = props.Translatable({"en": "Netflix clickstream", "nl": "Netflix clickstream"})
        table = props.PropsUIPromptConsentFormTable("netflix_clickstream", table_title, df) 
        tables_to_render.append(table)

    # Extract my list
    df = netflix.my_list_to_df(netflix_zip, selected_user)
    if not df.empty:
        table_title = props.Translatable({"en": "Netflix bookmarks", "nl": "Netflix bookmarks"})
        table = props.PropsUIPromptConsentFormTable("netflix_my_list", table_title, df) 
        tables_to_render.append(table)

    # Extract Indicated preferences
    df = netflix.indicated_preferences_to_df(netflix_zip, selected_user)
    if not df.empty:
        table_title = props.Translatable({"en": "Netflix indicated preferences", "nl": "Netflix indicated preferences"})
        table = props.PropsUIPromptConsentFormTable("netflix_indicated_preferences", table_title, df) 
        tables_to_render.append(table)

    # Extract playback related events
    df = netflix.playback_related_events_to_df(netflix_zip, selected_user)
    if not df.empty:
        table_title = props.Translatable({"en": "Netflix playback related events", "nl": "Netflix playback related events"})
        table = props.PropsUIPromptConsentFormTable("netflix_playback", table_title, df) 
        tables_to_render.append(table)

    # Extract search history
    df = netflix.search_history_to_df(netflix_zip, selected_user)
    if not df.empty:
        table_title = props.Translatable({"en": "Netflix search history", "nl": "Netflix search history"})
        table = props.PropsUIPromptConsentFormTable("netflix_search", table_title, df) 
        tables_to_render.append(table)

    # Extract messages sent by netflix
    df = netflix.messages_sent_by_netflix_to_df(netflix_zip, selected_user)
    if not df.empty:
        table_title = props.Translatable({"en": "Netflix messages", "nl": "Netflix messages"})
        table = props.PropsUIPromptConsentFormTable("netflix_messages", table_title, df) 
        tables_to_render.append(table)

    return tables_to_render





def extract_users(netflix_zip):
    """
    Reads viewing activity and extracts users from the first column
    returns list[str]
    """
    b = unzipddp.extract_file_from_zip(netflix_zip, "ViewingActivity.csv")
    df = unzipddp.read_csv_from_bytes_to_df(b)
    users = netflix.extract_users_from_df(df)
    return users


##########################################################################################
# Questionnaires

def render_questionnaire(progress):
    questions = [
        props.PropsUIQuestionOpen(question=UNDERSTANDING, id=1),
        props.PropsUIQuestionMultipleChoice(question=INDENTIFY_CONSUMPTION, id=2, choices=IDENTIFY_CONSUMPTION_CHOICES),
        props.PropsUIQuestionMultipleChoice(question=ENJOYMENT, id=3, choices=ENJOYMENT_CHOICES),
        props.PropsUIQuestionOpen(question=ADDITIONAL_COMMENTS, id=4),
    ]

    description = props.Translatable({"en": "Lorem ipsum dolor sit amet", "nl": "Lorem ipsum"})
    header = props.PropsUIHeader(props.Translatable({"en": "ASD", "nl": "ASD"}))
    body = props.PropsUIPromptQuestionnaire(questions=questions, description=description)
    footer = props.PropsUIFooter(progress)

    page = props.PropsUIPageDonation("ASD", header, body, footer)
    return CommandUIRender(page)


def render_questionnaire_no_donation(progress):
    questions = [
        props.PropsUIQuestionOpen(question=UNDERSTANDING, id=1),
        props.PropsUIQuestionMultipleChoice(question=INDENTIFY_CONSUMPTION, id=2, choices=IDENTIFY_CONSUMPTION_CHOICES),
        props.PropsUIQuestionMultipleChoice(question=ENJOYMENT, id=3, choices=ENJOYMENT_CHOICES),
        props.PropsUIQuestionOpen(question=NO_DONATION_REASONS, id=5),
        props.PropsUIQuestionOpen(question=ADDITIONAL_COMMENTS, id=4),
    ]

    description = props.Translatable({"en": "Lorem ipsum dolor sit amet", "nl": "Lorem ipsum"})
    header = props.PropsUIHeader(props.Translatable({"en": "ASD", "nl": "ASD"}))
    body = props.PropsUIPromptQuestionnaire(questions=questions, description=description)
    footer = props.PropsUIFooter(progress)

    page = props.PropsUIPageDonation("ASD", header, body, footer)
    return CommandUIRender(page)


##########################################
# Functions provided by Eyra did not change

def render_end_page():
    page = props.PropsUIPageEnd()
    return CommandUIRender(page)


def render_donation_page(platform, body, progress):
    header = props.PropsUIHeader(props.Translatable({"en": platform, "nl": platform}))

    footer = props.PropsUIFooter(progress)
    page = props.PropsUIPageDonation(platform, header, body, footer)
    return CommandUIRender(page)


def retry_confirmation(platform):
    text = props.Translatable(
        {
            "en": f"Unfortunately, we could not process your {platform} file. If you are sure that you selected the correct file, press Continue. To select a different file, press Try again.",
            "nl": f"Helaas, kunnen we uw {platform} bestand niet verwerken. Weet u zeker dat u het juiste bestand heeft gekozen? Ga dan verder. Probeer opnieuw als u een ander bestand wilt kiezen."
        }
    )
    ok = props.Translatable({"en": "Try again", "nl": "Probeer opnieuw"})
    cancel = props.Translatable({"en": "Continue", "nl": "Verder"})
    return props.PropsUIPromptConfirm(text, ok, cancel)


def prompt_file(extensions, platform):
    description = props.Translatable(
        {
            "en": f"Please follow the download instructions and choose the file that you stored on your device. Click “Skip” at the right bottom, if you do not have a file from {platform}.",
            "nl": f"Volg de download instructies en kies het bestand dat u opgeslagen heeft op uw apparaat. Als u geen {platform} bestand heeft klik dan op “Overslaan” rechts onder."
        }
    )
    return props.PropsUIPromptFileInput(description, extensions)


def donate(key, json_string):
    return CommandSystemDonate(key, json_string)

def exit(code, info):
    return CommandSystemExit(code, info)
