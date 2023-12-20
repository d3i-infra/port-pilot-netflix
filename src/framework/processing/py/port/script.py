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
    "nl": "Hoe zou u de gegevens omschrijven die u heeft gedeeld met onderzoekers van Universiteit Utrecht?"
})

INDENTIFY_CONSUMPTION = props.Translatable({"en": "In case you looked at the data presented on this page, did you recognise your Netflix watching patterns?", "nl": "Als u naar uw data gekeken hebt, in hoeverre herkent u uw eigen kijkgedrag?"})
IDENTIFY_CONSUMPTION_CHOICES = [
    props.Translatable({"en": "I recognized my Netflix watching patterns", "nl": "Ik herkende mijn Netflix kijkgedrag"}),
    props.Translatable({"en": "I recognized my Netflix watching patterns and patters of those I share my account with", "nl": "Ik herkende mijn eigen Netflix kijkgedrag en die van anderen met wie ik mijn account deel"}),
    props.Translatable({"en": "I recognized mostly the watching patterns of those I share my account with", "nl": "Ik herkende vooral het kijkgedrag van anderen met wie ik mijn account deel"}),
    props.Translatable({"en": "I did not look at my data ", "nl": "Ik heb niet naar mijn gegevens gekeken"}),
    props.Translatable({"en": "Other", "nl": "Anders"})
]

ENJOYMENT = props.Translatable({"en": "In case you looked at the data presented on this page, how interesting did you find looking at your data?", "nl": "Als u naar uw data hebt gekeken, hoe interessant vond u het om daar naar te kijken?"})
ENJOYMENT_CHOICES = [
    props.Translatable({"en": "not at all interesting", "nl": "Helemaal niet interessant"}),
    props.Translatable({"en": "somewhat uninteresting", "nl": "Een beetje oninteressant"}),
    props.Translatable({"en": "neither interesting nor uninteresting", "nl": "Niet interessant, niet oninteressant"}),
    props.Translatable({"en": "somewhat interesting", "nl": "Een beetje interessant"}),
    props.Translatable({"en": "very interesting", "nl": "Erg interessant"})
]

ADDITIONAL_COMMENTS = props.Translatable({
    "en": "Do you have any additional comments about the donation? Please add them here.",
    "nl": "Heeft u nog andere opmerkingen? Laat die hier achter."
})

#Not donate questions
NO_DONATION_REASONS = props.Translatable({
    "en": "What is/are the reason(s) that you decided not to donate your data?",
    "nl": "Wat is de reden dat u er voor gekozen hebt uw data niet te doneren?"
})

# Headers
SUBMIT_FILE_HEADER = props.Translatable({
    "en": "Select your Netflix file", 
    "nl": "Selecteer uw Netflix bestand"
})

REVIEW_DATA_HEADER = props.Translatable({
    "en": "Your Netflix data", 
    "nl": "Uw Netflix gegevens"
})

RETRY_HEADER = props.Translatable({
    "en": "Try again", 
    "nl": "Probeer opnieuw"
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
        file_result = yield render_donation_page(SUBMIT_FILE_HEADER, promptFile, progress)
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

                if len(users) == 1:
                    selected_user = users[0]
                    extraction_result = extract_netflix(file_result.value, selected_user, group_label)
                    table_list = extraction_result
                elif len(users) > 1:
                    selection = yield prompt_radio_menu_select_username(users, progress)
                    if selection.__type__ == "PayloadString":
                        selected_user = selection.value
                        extraction_result = extract_netflix(file_result.value, selected_user, group_label)
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
                retry_result = yield render_donation_page(RETRY_HEADER, retry_confirmation(platform_name), progress)

                if retry_result.__type__ == "PayloadTrue":
                    continue
                else:
                    LOGGER.info("Skipped during retry ending flow")
                    yield donate_logs(f"{session_id}-tracking")
                    yield donate_status(f"{session_id}-SKIP-RETRY-FLOW", "SKIP_RETRY_FLOW")
                    break

            # Enter retry flow, reason: valid DDP but no users could be extracted
            if selected_user == "":
                LOGGER.info("Selected user is empty after selection, enter retry flow")
                yield donate_logs(f"{session_id}-tracking")
                retry_result = yield render_donation_page(RETRY_HEADER, retry_confirmation(platform_name), progress)

                if retry_result.__type__ == "PayloadTrue":
                    continue
                else:
                    LOGGER.info("Skipped during retry ending flow")
                    yield donate_logs(f"{session_id}-tracking")
                    yield donate_status(f"{session_id}-SKIP-RETRY-FLOW", "SKIP_RETRY_FLOW")
                    break

        else:
            LOGGER.info("Skipped at file selection ending flow")
            yield donate_logs(f"{session_id}-tracking")
            yield donate_status(f"{session_id}-SKIP-FILE-SELECTION", "SKIP_FILE_SELECTION")
            break

        # STEP 2: ask for consent
        progress += step_percentage

        if table_list is not None:
            LOGGER.info("Prompt consent; %s", platform_name)
            yield donate_logs(f"{group_label}-{session_id}-tracking")
            prompt = create_consent_form(table_list)
            consent_result = yield render_donation_page(REVIEW_DATA_HEADER, prompt, progress)

            # Data was donated
            if consent_result.__type__ == "PayloadJSON":
                LOGGER.info("Data donated; %s", platform_name)
                yield donate(f"{group_label}-{platform_name}", consent_result.value)
                yield donate_logs(f"{group_label}-{session_id}-tracking")
                yield donate_status(f"{session_id}-DONATED", "DONATED")

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
                yield donate_status(f"{session_id}-SKIP-REVIEW-CONSENT", "SKIP_REVIEW_CONSENT")

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


def donate_status(filename: str, message: str):
    return donate(filename, json.dumps({"status": message}))


def prompt_radio_menu_select_username(users, progress):
    """
    Prompt selection menu to select which user you are
    """

    title = props.Translatable({ "en": "Select your Netflix profile name", "nl": "Kies jouw Netflix profielnaam" })
    description = props.Translatable({ "en": "", "nl": "" })
    header = props.PropsUIHeader(props.Translatable({"en": "", "nl": ""}))

    radio_items = [{"id": i, "value": username} for i, username in enumerate(users)]
    body = props.PropsUIPromptRadioInput(title, description, radio_items)
    footer = props.PropsUIFooter(progress)

    page = props.PropsUIPageDonation("Netflix", header, body, footer)

    return CommandUIRender(page)


##################################################################
# Extraction function

# The A conditional group gets the visualizations 
def extract_netflix(netflix_zip: str, selected_user: str, group_label: str) -> list[props.PropsUIPromptConsentFormTable]:
    """
    Main data extraction function
    Assemble all extraction logic here, results are stored in a dict
    """

    tables_to_render = []
    
    # Extract the ratings
    ###################################################################

    df = netflix.ratings_to_df(netflix_zip, selected_user)
    if not df.empty:
        if group_label == "A":
            table_title = props.Translatable({"en": "Your ratings on Netflix", "nl": "Uw beoordelingen op Netflix"})
            table_description = props.Translatable({
                "en": "The size of the words in the figure below indicates how many positive ratings ('thumbs up') you have given to a program or movie on Netflix. Click 'Show Table' to view these ratings per row.", 
                "nl": "De grootte van de woorden in het figuur hieronder geven aan hoeveel positieve beoordelingen (‘duimpjes omhoog’) u aan een programma of film heeft gegeven op Netflix. Klik op ‘Tabel tonen’ om deze beoordelingen per rij te bekijken."
            })
            wordcloud = props.PropsUITextVisualization(
                title=props.Translatable({"en": "Number of thumbs up", "nl": "Aantal duimpjes omhoog"}),
                type="wordcloud",
                text_column="Titel",
                value_column="Aantal duimpjes omhoog",
                value_aggregation="mean"      
            )
            table = props.PropsUIPromptConsentFormTable("netflix_rating", table_title, df, table_description, [wordcloud])
            tables_to_render.append(table)

        if group_label == "B":
            table_title = props.Translatable({"en": "Your ratings on Netflix", "nl": "Uw beoordelingen op Netflix"})
            table_description = props.Translatable({
                "en": "Click 'Show Table' to view these ratings per row.", 
                "nl": "Klik op ‘Tabel tonen’ om deze beoordelingen per rij te bekijken."
            })
            table = props.PropsUIPromptConsentFormTable("netflix_rating", table_title, df, table_description)
            tables_to_render.append(table)

    # Extract the viewing activity
    ###################################################################

    df = netflix.viewing_activity_to_df(netflix_zip, selected_user)
    if not df.empty:
        if group_label == "A":
            table_title = props.Translatable({"en": "What you watched", "nl": "Wanneer kijkt u Netflix"})
            table_description = props.Translatable({
                "en": "This table shows what titles you watched when, for how long, and on what device. The two graphs show how much time you spent watching Netflix content", 
                "nl": """ In de eerste figuur hieronder ziet u het aantal uren dat u naar Netflix heeft gekeken sinds u Netflix gebruikt. In de tweede figuur hieronder ziet u het totaal aantal uren dat u naar Netflix heeft gekeken per uur van de dag.
    Klik op ‘Tabel tonen’ om voor elke keer dat u iets op Netflix heeft gekeken te zien welke serie of film dit was, wanneer u dit heeft gekeken, hoe lang u het heeft gekeken en op welk apparaat u het heeft gekeken."""
            })

            date_graph = props.PropsUIChartVisualization(
                title=props.Translatable({"en": "Hours Netflix watched", "nl": "Aantal uren naar Netflix gekeken over tijd"}),
                type="area",
                group= props.PropsUIChartGroup(column="Start tijd", label='Datum', dateFormat="auto"),
                values= [props.PropsUIChartValue(label='Uren Netflix gekeken', column='Aantal uur gekeken', aggregate="sum", addZeroes= True)]
            )
            hour_graph = props.PropsUIChartVisualization(
                title=props.Translatable({"en": "At what time of the day do you watch?", "nl": "Op welk moment van de dag kijkt u?"}),
                type="bar",
                group= props.PropsUIChartGroup(column="Start tijd", label='Uur van de dag', dateFormat="hour_cycle"),
                values= [props.PropsUIChartValue(label='Aantal uur gekeken', column='Aantal uur gekeken', aggregate="sum", addZeroes= True)]
            )
            table = props.PropsUIPromptConsentFormTable("netflix_viewings", table_title, df, table_description, [date_graph, hour_graph]) 
            tables_to_render.append(table)

        if group_label == "B":
            table_title = props.Translatable({"en": "What you watched", "nl": "Wanneer kijkt u Netflix"})
            table_description = props.Translatable({
                "en": "This table shows what titles you watched when, for how long, and on what device.", 
                "nl": "Klik op ‘Tabel tonen’ om voor elke keer dat u iets op Netflix heeft gekeken te zien welke serie of film dit was, wanneer u dit heeft gekeken, hoe lang u het heeft gekeken en op welk apparaat u het heeft gekeken."
            })
            table = props.PropsUIPromptConsentFormTable("netflix_viewings", table_title, df, table_description)
            tables_to_render.append(table)

    # Extract the clickstream
    ###################################################################
    df = netflix.clickstream_to_df(netflix_zip, selected_user)
    if not df.empty:
        table_description = props.Translatable({
            "en": "This table shows how you used the Netflix interface for finding content and learning more about titles. It includes the device you used and the specific times you clicked on a button in the Netflix interface (e.g., movie details, search bar)", 
            "nl": "Klik op ‘Tabel tonen’ om te zien welke opties in Netflix u heeft gebruikt om series en films te vinden, wanneer u deze opties heeft gebruikt en met welk apparaat. Het gaat om opties zoals de zoekfunctie of door middel van advertenties die Netflix aan u heeft laten zien."
        })
        table_title = props.Translatable({"en": "Which Netflixs functions you used", "nl": "Welke Netflix functies u heeft gebruikt"})
        table = props.PropsUIPromptConsentFormTable("netflix_clickstream", table_title, df, table_description) 
        tables_to_render.append(table)

    # Extract my list
    df = netflix.my_list_to_df(netflix_zip, selected_user)
    if not df.empty:
        table_description = props.Translatable({
            "en": "This table shows which titles you added to your watch list and on what dates",
            "nl": "Klik op ‘Tabel tonen’ om te zien welke titels u heeft toegevoegd aan ‘Mijn lijst’ en wanneer u dit heeft gedaan. In ‘Mijn lijst’ heeft u bijvoorbeeld series en films opgeslagen die u graag nog wilt zien."
        })
        table_title = props.Translatable({"en": "What you added to your watch list", "nl": "Wat u aan uw watch list heeft toegevoegd"})
        table = props.PropsUIPromptConsentFormTable("netflix_my_list", table_title, df, table_description) 
        tables_to_render.append(table)

    # Extract Indicated preferences
    df = netflix.indicated_preferences_to_df(netflix_zip, selected_user)
    if not df.empty:
        table_description = props.Translatable({
            "en": "This table shows what titles you watched and whether you listed them as preferences (i.e, liked, added to your list)",
            "nl": "Deze tabel toont welke titels u hebt bekeken en of u ze hebt aangemerkt als voorkeuren (d.w.z. leuk gevonden, toegevoegd aan uw lijst)"
        })
        table_title = props.Translatable({"en": "What you watched and listed as a preference", "nl": "Wat u heeft bekeken en als voorkeur heeft opgegeven"})
        table = props.PropsUIPromptConsentFormTable("netflix_indicated_preferences", table_title, df, table_description) 
        tables_to_render.append(table)

    # Extract playback related events
    df = netflix.playback_related_events_to_df(netflix_zip, selected_user)
    if not df.empty:
        table_description = props.Translatable({
            "nl": "Klik op ‘Tabel tonen’ om per serie of film te zien hoevaak u pauze heeft genomen, of heeft teruggespoeld.",
            "en": "This table shows what titles you watched from which devices at what time and date. It also includes how often you started, stopped, pressed play, and pressed pause per title"
        })
        table_title = props.Translatable({"en": "How you watched netflix content", "nl": "Hoevaak neemt u pauze tijdens het kijken naar series en films op Netflix?"})
        table = props.PropsUIPromptConsentFormTable("netflix_playback", table_title, df, table_description) 
        tables_to_render.append(table)

    # Extract search history
    df = netflix.search_history_to_df(netflix_zip, selected_user)
    if not df.empty:
        table_description = props.Translatable({
            "nl": "Klik op ‘Tabel tonen’ om  te zien naar welke series en films u heeft gezocht en welke zoektermen u heeft gebruikt om dit te vinden. U ziet ook of u de gevonden serie of film vervolgens heeft gekeken of aan ‘Mijn lijst’ heeft toegevoegd.",
            "en": "This table shows which titles you have searched for. It includes the device you used for searching, whether the title was searched in the kid-friendly account, the search terms you used, the result that was shown to you, and how you proceeded with that result (did you add it to your watch list or play it immediately?). It also shows in which section of Netflix you found the title and when you did the search query"
        })
        table_title = props.Translatable({"en": "Your search history", "nl": "Uw zoekgeschiedenis"})
        table = props.PropsUIPromptConsentFormTable("netflix_search", table_title, df, table_description) 
        tables_to_render.append(table)

    # Extract messages sent by netflix
    df = netflix.messages_sent_by_netflix_to_df(netflix_zip, selected_user)
    if not df.empty:

        table_description = props.Translatable({
            "nl": "Klik op ‘Tabel tonen’ om te zien welke reclame berichten u van Netflix heeft ontvangen, bijvoorbeeld over nieuwe series of films. U ziet ook of u de getoonde serie of film vervolgens heeft gekeken.",
            "en": "This table shows what promotional messages you received from Netflix about new titles. It includes the time you received the message, the type of notification, the channel through which it was sent, which specific title was promoted in the message, and whether you clicked on the message, along with the frequency of such clicks"
        })
        table_title = props.Translatable({"en": "Messages that you received from Netflix", "nl": "Berichten van Netflix"})
        table = props.PropsUIPromptConsentFormTable("netflix_messages", table_title, df, table_description) 
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

    description = props.Translatable({"en": "Below you can find a couple of questions about the data donation process", "nl": "Hieronder vind u een paar vragen over het data donatie process"})
    header = props.PropsUIHeader(props.Translatable({"en": "Questionnaire", "nl": "Vragenlijst"}))
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

    description = props.Translatable({"en": "Below you can find a couple of questions about the data donation process", "nl": "Hieronder vind u een paar vragen over het data donatie process"})
    header = props.PropsUIHeader(props.Translatable({"en": "Questionnaire", "nl": "Vragenlijst"}))
    body = props.PropsUIPromptQuestionnaire(questions=questions, description=description)
    footer = props.PropsUIFooter(progress)

    page = props.PropsUIPageDonation("ASD", header, body, footer)
    return CommandUIRender(page)


##########################################
# Functions provided by Eyra did not change

def render_end_page():
    page = props.PropsUIPageEnd()
    return CommandUIRender(page)


def render_donation_page(header_text, body, progress):
    header = props.PropsUIHeader(header_text)

    footer = props.PropsUIFooter(progress)
    platform = "Netflix"
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
            "en": f"Please follow the download instructions and choose the file that you stored on your device.",
            "nl": f"Volg de download instructies en kies het bestand dat u opgeslagen heeft op uw apparaat."
        }
    )
    return props.PropsUIPromptFileInput(description, extensions)


def donate(key, json_string):
    return CommandSystemDonate(key, json_string)

def exit(code, info):
    return CommandSystemExit(code, info)
