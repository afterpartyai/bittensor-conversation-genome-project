import json
import os
import random
import sqlite3
import time

from models.conversation_record import ConversationRecord
from prometheus_client import CONTENT_TYPE_LATEST
from prometheus_client import generate_latest
from Utils import Utils

from conversationgenome.prompt_chain.PromptChainStep import PromptChainStep
from conversationgenome.scoring_mechanism.TaggingExampleOutput import (
    TaggingExampleOutput,
)
from conversationgenome.task_bundle.ConversationTaggingTaskBundle import (
    ConversationInput,
)
from conversationgenome.task_bundle.ConversationTaggingTaskBundle import (
    ConversationInputData,
)
from conversationgenome.task_bundle.ConversationTaggingTaskBundle import (
    ConversationTaggingTaskBundle,
)
from conversationgenome.task_bundle.TaskBundle import TaskBundle
from conversationgenome.task_bundle.WebpageMetadataGenerationTaskBundle import (
    WebpageMarkdownInput,
)
from conversationgenome.task_bundle.WebpageMetadataGenerationTaskBundle import (
    WebpageMarkdownInputData,
)
from conversationgenome.task_bundle.WebpageMetadataGenerationTaskBundle import (
    WebpageMetadataGenerationTaskBundle,
)
from web.middlewares.authentication_middleware import AuthMiddleware
from web.middlewares.metrics_middleware import MetricsMiddleware

ss58_decode = None
try:
    from scalecodec.utils.ss58 import ss58_decode
except:
    print("scalecodec is not installed. Try: pip install scalecodec")


CYAN = "\033[96m"  # field color
GREEN = "\033[92m"  # indicating success
RED = "\033[91m"  # indicating error
YELLOW = '\033[0;33m'
COLOR_END = '\033[m'
DIVIDER = '_' * 120

# Test convo read endpoint:
# curl -XPOST https://api.conversations.xyz/api/v1/conversation/reserve | python -m json.tool
# curl -XPOST http://localhost:8000/api/v1/conversation/reserve | python -m json.tool

# Test convo write endpoint:
# curl -XPOST http://localhost:8000/api/v1/conversation/reserve | python -m json.tool

from fastapi import FastAPI
from fastapi import Request
from fastapi import Response

app = FastAPI()
app.add_middleware(MetricsMiddleware)
app.add_middleware(AuthMiddleware)


class Db:
    source_type = 2  # Non-CGP
    db_name = None
    table_name = None
    sql_create_results = """CREATE TABLE IF NOT EXISTS cgp_results (
	"id"	INTEGER UNIQUE,
	"status"	INTEGER DEFAULT 1,
	"batch_num"	INTEGER,
	"c_guid"	TEXT,
	"convo_window_index"	INTEGER DEFAULT 1,
	"source_type"	INTEGER DEFAULT 2,
	"mode"	TEXT,
	"hotkey"	TEXT,
	"coldkey"	TEXT,
	"uid"	INTEGER,
	"llm_type"	TEXT,
	"model"	TEXT,
	"tags"	JSON,
	"marker_id"	INTEGER,
	"json"	JSON,
	"created_at"	TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	"cgp_version"	TEXT
	"updated_at"	TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	"updated_by"	INTEGER,
	"created_by"	INTEGER,
	PRIMARY KEY("id" AUTOINCREMENT)
)"""

    def __init__(self, db_name, table_name):
        self.db_name = db_name
        self.table_name = table_name

    def get_cursor(self):
        db_name = os.path.join(os.path.dirname(__file__), 'conversations.sqlite')
        conn = sqlite3.connect(db_name)
        conn.row_factory = Db.dict_factory
        cursor = conn.cursor()

        return cursor

    def insert_into_table(self, c_guid, content):
        today = Utils.get_time("%Y.%m.%d")
        db_name = f"{self.db_name}_{today}.sqlite"
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute(self.sql_create_results)
        updateRow = {
            "c_guid": c_guid,
            "mode": Utils.get(content, "mode"),
            "model": Utils.get(content, "model"),
            "llm_type": Utils.get(content, "llm_type"),
            "convo_window_index": Utils.get(content, "convo_window_index"),
            "marker_id": Utils.get(content, "marker_id"),
            "source_type": self.source_type,
            "hotkey": Utils.get(content, "hotkey"),
            "coldkey": Utils.get(content, "coldkey"),
            "batch_num": Utils.get(content, "batch_num"),
            "tags": Utils.get(content, "tags"),
            "cgp_version": Utils.get(content, "cgp_version"),
            "json": json.dumps(content),
        }
        fields = []
        questions = []
        values = []
        for field, val in updateRow.items():
            fields.append(field)
            questions.append("?")
            values.append(val)
        fields_str = ",".join(fields)
        questions_str = ",".join(questions)
        cursor.execute(f"INSERT INTO cgp_results ({fields_str}) VALUES ({questions_str})", (values))
        conn.commit()
        conn.close()

    def get_random_conversation(self) -> ConversationRecord:
        cursor = self.get_cursor()
        sql = 'SELECT * FROM conversations ORDER BY RANDOM() LIMIT 1'
        cursor.execute(sql)
        rows = cursor.fetchall()
        if rows and len(rows) == 1:
            return ConversationRecord(**rows[0])
        else:
            return None

    def get_conversation(self, guid):
        cursor = self.get_cursor()
        cursor.execute("SELECT * FROM conversations WHERE guid = ?", (guid,))
        rows = cursor.fetchall()
        if rows and len(rows) == 1:
            return rows[0]
        else:
            return None

    @staticmethod
    def dict_factory(cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            if col[0] == "json":
                try:
                    d["data"] = json.loads(row[idx])
                except:
                    d["data"] = json.loads("{}")
            else:
                d[col[0]] = row[idx]
        return d


@app.get("/")
def get_request():
    return {"message": "Forbidden"}


@app.post("/api/v1/conversation/reserve")
def post_request() -> TaskBundle:
    # Used for testing long or bad responses
    if False:
        time.sleep(30)

    try:
        db = Db("conversations", "conversations")
        # By default, the API will return a random conversation from the database
        # Comment it if you want to test a specific conversation
        conversation: ConversationRecord = db.get_random_conversation()

        # If you want the API to return a specific conversation for testing purposes
        # Uncomment the line below
        # Pass the c_guid of the conversation you want!

        # conversation = db.get_conversation(guid="6982")

        convo = {
            "guid": conversation.data.guid,
            "lines": conversation.data.lines,
        }

        convo['total'] = len(convo['lines'])

        # Anonymize the participants
        participants = conversation.data.participants
        out_participants = []
        p_count = 0

        for key, participant in participants.items():
            out_participants.append(f"SPEAKER_{participant.idx}")
            p_count += 1

        convo['participants'] = out_participants

        webpage_tagging_task_guid = "1632375642"
        webpage_markdown_input_data_lines = [
            [
                0,
                "<markdown>STUDENT RESOURCES | MUSEO Art Academy\ntop of page\n[MUSEO Art Academy](https://www.museoartacademy.com)\n* [HOME](https://www.museoartacademy.com)\n  + [Contact Us](https://www.museoartacademy.com/contact-us)\n* [CLASSES](https://www.museoartacademy.com/classes)\n  + [AGES 4-6](https://www.museoartacademy.com/ages-4-6)\n  + [AGES 5-9](https://www.museoartacademy.com/classes-ages-5-9)\n  + [AGES 8-13](https://www.museoartacademy.com/classes-ages-8-13)\n  + [AGES 11-19](https://www.museoartacademy.com/classes-ages-11-19)\n  + [Private Pottery Wheel Lessons](https://www.museoartacademy.com/private-lessons)\n* [CAMPS](https://www.museoartacademy.com/camps)\n  + [Summer Camps](https://www.museoartacademy.com/summer-camps)\n  + [Spring Break Camps](https://www.museoartacademy.com/spring-break-camps)\n* [PARTIES](https://www.museoartacademy.com/parties)\n* [FREE TRIAL](https://www.museoartacademy.com/free-trial)\n* MORE\n  + [STUDENT RESOURCES](https://www.museoartacademy.com/student-resources)\n  + [Instructors](https://www.museoartacademy.com/instructors)\n  + [Policies](https://www.museoartacademy.com/policies)\n  + [Forms](https://www.museoartacademy.com/forms)\n  + [Discounts](https://www.museoartacademy.com/discounts)\n  + [Review Us](https://www.museoartacademy.com/review-us)\nstudent resources\n=================\nPARENT DASHBOARD\n[download the MUSEO app](https://museoartacademy.app.link/gXEFvOmBTyb)\n[SUBMIT AN ABSENCE](https://www.museoartacademy.com/student-resources)\n[Access My Account](https://www.museoartacademy.com/student-resources)\n[Manage My Enrollment](https://www.museoartacademy.com/student-resources)\n[Enroll in a Class](https://www.museoartacademy.com/classes)\n[Enroll in a Camp](https://www.museoartacademy.com/camps)\n[View Programs Calendar](https://www.museoartacademy.com/student-resources)\n[Review Us Online](https://www.museoartacademy.com/student-resources)\n![MUSEO app QR](https://static.wixstatic.com/media/d1b711_691776729bfb4bfba6013ae9352d5fb0~mv2.jpg/v1/fill/w_196,h_200,al_c,lg_1,q_80,enc_avif,quality_auto/MUSEO%20app%20QR_edited.jpg)\n[download the MUSEO app](https://museoartacademy.app.link/gXEFvOmBTyb)\nACCESS MY ACCOUNT\nsubmit absence | schedule makeup | add student | update account and billing info\nJump to the [Manage My Enrollment](https://www.museoartacademy.com/student-resources) section to transfer, temporarily pause, or drop from a class.\n[​](https://app2.jackrabbitclass.com/portal/ppLogin.asp?id=503941)\n​\n​\n[ACCOUNT LOG IN](https://app2.jackrabbitclass.com/jr3.0/ParentPortal/Login?orgId=503941)\nREVIEW US ONLINE\nIf you're enjoying your experience with us, we'd LOVE it if you would please take a quick minute to review us online. We put a lot of hard work into our programs and appreciate your support to help others learn more about us. Simply click on one of the platform options listed below.   \n​  \n​Your 5-STAR review tells us that you might want to spend more time here with us, wooooo hooooo, thank you!!  \nAll 5-STAR reviews go into a year-end drawing to win a FREE ART PARTY ($295 value).\n[Post a review on Google](https://www.google.com/maps/place//data=!4m3!3m2!1s0x54906f806cad57af:0x43900165486bd62e!12e1?source=g.page.m.dd._&laa=lu-desktop-reviews-dialog-review-solicitation)\n[Post a review on Yelp](https://www.yelp.com/writeareview/biz/ZD7yg5qvS0iGQ_rfmhpEQw?return_url=%2Fbiz%2FZD7yg5qvS0iGQ_rfmhpEQw)\n[Post a review on Facebook](https://www.facebook.com/MuseoArtAcademy/reviews)\n[Fave and recommend us on Nextdoor](https://nextdoor.com/pages/museo-art-academy-issaquah-wa/)\nIf we are not meeting and exceeding your expectations in any way, PLEASE don't hesitate to let us know. Your feedback is a valued gift and we're committed to using it to make improvements where needed to be the best we can be!\n[ClientServices.Museo@outlook.com](mailto:ClientServices.MUSEO@outlook.com?subject=Providing%20Constructive%20Feedback)\n[425-391-0244](tel:+1-425-391-0244)\nMAKEUPS\nOne makeup per month is permitted for a submitted absence in our in-person weekly studio classes. NO SHOW absences are not eligible for makeup.\n​\nSimply [log in to your account](https://www.museoartacademy.com/student-resources) then complete the following steps to submit an upcoming absence. Please allow two (Mon-Fri) business days for the absence to be confirmed in our system before attempting to schedule a makeup for it.\n[ACCOUNT LOG IN](https://app2.jackrabbitclass.com/jr3.0/ParentPortal/Login?orgId=503941)\nHOW TO SUBMIT AN ABSENCE\n* Click on MENU icon in upper right corner of the screen\n* Click on ABSENCES & MAKEUPS\n* Click the green SUBMIT AN ABSENCE button then follow the prompts\nIMPORTANT NOTE: After you submit an upcoming absence, we'll need to manually mark it \"eligible for makeup\" on our end. Please allow two (Mon-Fri) business days for us to do so (we'll try to do it sooner). When you return to your account and see a green SCHEDULE MAKEUP link showing on the submitted absence, it means it's updated and ready to be scheduled.  \n  \n​HOW TO SCHEDULE A MAKEUP  \nDo this at least two (Mon-Fri) business days after submitting the absence.\n* Click on the listed absence (scroll down to view past absences)\n* Click on the green SCHEDULE MAKEUP link listed on the absence\n* Scroll down to view the full list of available options\n* Click the SELECT button on the desired makeup\\*\n* Click the blue SUBMIT button\nHOW TO RESCHEDULE A MAKEUP\n* Pull up the absence on your account\n* Click on the blue \"Scheduled for X date\" link located at the bottom right. This will open your current makeup.\n* You'll see a red \"Cancel This Makeup\" button. Once you click on that (and confirm your decision) you'll be able to reselect a different makeup.\n\\*Makeups are intended to take place during the month immediately following the end of the scheduled lesson in which the absence occurred. This provides the student additional time in our studio with an instructor to properly complete that lesson. \n​\n​\n[ACCOUNT LOG IN](https://app2.jackrabbitclass.com/jr3.0/ParentPortal/Login?orgId=503941)\nAVAILABLE MAKEUPS\n​\n[ACCOUNT LOG IN](https://app2.jackrabbitclass.com/jr3.0/ParentPortal/Login?orgId=503941)\nMAKEUP FAQs\nWhat is a makeup?\n> A makeup is an OPTIONAL, one-hour, instructor-led OPEN STUDIO event for students of all ages. It is designed to provide students additional time in our studio with an instructor's assistance to complete an unfinished project due to an excused absence. By default, the instructor will help the student catch up during their regular class time following an absence so that they are on pace with the rest of the class for the remainder of the lesson. The makeup session will not be presenting/teaching specifics of any lesson but rather providing supervised time in our studio for students to complete their work.\n> ​\nWhat is an excused absence?\n> An absence is considered excused when you've submitted it on your account prior to the class you'll be missing. Failure to submit an absence in advance results in a 'NO SHOW' which is not eligible for makeup. Verbal notification to the instructor or any MUSEO staff member is not accepted.\n> ​\nDoes my student need a makeup?\n> A makeup is not necessary if a student has completed all their work within the standard class time. That being said, students are still welcome to attend a makeup for up to one submitted (excused) absence each month, if desired. In this case the makeup instructor will assign a \"continued learning\" activity in which the student will further explore and practice concepts and techniques that were covered in the regular class they missed.\n> ​\nMy student attends a MUSEO class online. What makeup options are available for them?\n> All online classes are recorded. Students who miss a class will be provided with a [recording of that missed lesson](https://www.museoart.com/recording-request.html) [upon request](https://www.museoart.com/recording-request.html). Note, the video is automatically deleted one week after the recording date.\n> ​\nHow many makeups may my student attend?\n> We will accommodate one makeup per lesson within our standard schedule of options for an excused absence.\nWhen are makeups offered?\n> Makeup sessions are offered during the second and third week of each month, typically on Fridays, Saturdays, and Sundays.\n> ​\nNone of the available makeups listed works with our schedule. What are our options?\n> We regularly provide a variety of makeups on weekdays and weekends. If you are unable to find an option that works for you, please let us know. We'll try to work something out for you. Please keep in mind that makeups are not guaranteed.\nMay my student attend more than one makeup per lesson if the additional absence is excused?  \n> Potentially (subject to available space). We do our best to accommodate multiple makeups when possible. In order to do so, we’ll need to place your student on the waitlist for the additional makeup. If a space is available as of two days prior to that makeup, we’ll notify you via email and then confirm the spot for your student. Please note that this is necessary to ensure that all students have an equal opportunity to make up one submitted (excused) absence. To waitlist your student, please [send us an email](mailto:clientservices.museo@outlook.com?subject=Please%20waitlist%20my%20student%20for%20an%20additional%20makeup) listing the desired makeup date(s). View list of available makeups [here](https://www.museoartacademy.com/student-resources#makeups-available).\n> ​\nMay my student attend a makeup if we did not submit their absence in advance? (absence was unexcused) \n> A \"no show\" absence is not eligible for a makeup.\n> ​\nWill the makeup be with my student's same instructor?\n> While the instructor who is leading the makeup may not necessarily be your student's regular instructor, they are very familiar with the curricula in all classes and able to assist all students as needed. ​\n> ​\nMay my student attend a different type of class as a makeup?\n> No. The opportunity to make up missed class time is limited to the specially designed makeups. If you are interested in trying out a different class, we offer [free trials](https://www.museoartacademy.com/free-trial) in all classes during the first week of each month.\n> ​\nHow soon after a submitted absence should my student attend a makeup?\n> Makeups are most effective when scheduled for a date that is soon after your student's regular class has completed the lesson during which your student's excused absence occured. Eligibility to attend a makeup will expire on the final day of the month following your student's excused absence. For example, a student with a Feb 1 excused absence will have an opportunity to attend any makeup during the entire month of March. The makeup eligibility expires March 31.\n>\n> ​​\nWhat happens if my student needs to miss their makeup?\n> You may reschedule or cancel a confirmed makeup up to 24 hours prior to the makeup. This can be done directly on [your account](https://www.museoartacademy.com/student-resources#access-my-account). A \"no-show\" will not be rescheduled.​\npause or drop?\n==============\nPAUSE ENROLLMENT  \nYour student's enrollment may be paused for up to two months. Their spot on the roster will be guaranteed for them when they return. They may choose to transfer to a different class if plans change. No tuition is charged for the time period that enrollment is paused.  \n​  \nImportant to note:\n* The request to pause must be received in advance of the paused enrollment time period.\n* Prepayment of tuition for the month of your student's return is required at the time you pause your enrollment.\n* Once selected, your return date cannot be pushed out. Returning later than your selected date will result in forfeiture of your prepayment.\n* Students who withdraw from class prior to the completion of the extended absence will forfeit their prepayment. Deposit will be subject to the standard withdrawal policy.​\n​​\nDROP FROM A WEEKLY CLASS  \nYour student's drop date will be scheduled for the final day of a calendar month only. Mid-month withdrawals are not permitted. Refund/credit for remaining weeks in a paid month will not be issued once payment for that month has been processed. (e.g. if a student chooses to drop prior to the end of the paid month, tuition will not be prorated, credited, or refunded).   \n​  \nImportant to note:\n* If you set your student's drop date for next month or later, your deposit will be applied toward your final month's class fees.\n* If you are withdrawing at the end of this current month, you will forfeit your non-refundable deposit.\n[PAUSE ENROLLMENT](https://www.museoartacademy.com/student-resources)\n[DROP FROM CLASS](https://www.museoartacademy.com/student-resources)\nMANAGE MY CLASS ENROLLMENT\n[transfer](https://www.museoartacademy.com/student-resources) | [pause](https://www.museoartacademy.com/student-resources) | [drop](https://www.museoartacademy.com/student-resources) ​| more info on pausing vs dropping\n##### Class Transfer\nStudent\nTransfer from\nFinal Date Attending\nTransfer To\nFirst Date Attending\nComment\nAuthorizing Parent\nParent's Email\nParent's Mobile Phone\nI accept terms & conditions\nSubmit Request\nThank you. Please allow two business days (M-F) to process.\n##### Temporarily Pause\nYour student's enrollment may be paused for up to TWO months. Their spot on the roster will be guaranteed for them when they return. They may choose to transfer to a different class if plans change. No tuition is charged for the time period that enrollment is paused.  \n​  \nImportant to note:\n* The request to pause must be received in advance of the paused enrollment time period.\n* Prepayment of tuition for the month of your student's return is required at the time you pause your enrollment.\n* Once selected, your return date cannot be pushed out. Returning later than your selected date will result in forfeiture of your prepayment.\n* Students who withdraw from class prior to the completion of the extended absence will forfeit their prepayment. Deposit will be subject to the standard withdrawal policy.\nStudent\nClass to pause\nPause Starting\nPause Duration\nComment\nAuthorizing Parent\nParent's Email\nParent's Mobile Phone\nI accept terms & conditions\nSubmit Request\nThank you. Please allow two business days (M-F) to process.\n##### Month-End Drop\nYour student's drop date will be scheduled for the final day of a calendar month only. Mid-month withdrawals are not permitted. Refund/credit for remaining weeks in a paid month will not be issued once payment for that month has been processed. (e.g. if a student chooses to drop prior to the end of the paid month, tuition will not be prorated, credited, or refunded).   \n​  \nImportant to note:\n* If you set your student's drop date for next month or later, your deposit will be applied toward your final month's class fees.\n* If you are withdrawing at the end of this current month, you will forfeit your non-refundable deposit.\nStudent\nDrop from class\nDrop Date\nReason for Drop\nComment\nAuthorizing Parent\nParent's Email\nParent's Mobile Phone\nI accept terms & conditions\nSubmit Request\nThank you. Please allow two business days (M-F) to process.\nTEMPORARILY PAUSING ENROLLMENT\nYour student's enrollment in a weekly class may be paused for up to two months. Their spot on the roster will be guaranteed for them when they return. They may choose to transfer to a different class if plans change. No tuition is charged for the period of time when enrollment is paused.\nImportant to note:\n* You must submit your request to pause in advance of the paused enrollment period of time.\n* Prepayment of tuition for the month of your student's return is required at the time you pause your enrollment.\n* Once selected, your return date cannot be pushed out. Returning later than your selected date will result in forfeiture of your prepayment.\n* Students who withdraw from class prior to the completion of the paused enrollment period of time will forfeit their prepayment. Deposit will be subject to the standard withdrawal policy.\n[PAUSE ENROLLMENT](https://www.museoartacademy.com/student-resources)\nDROPPING FROM A WEEKLY CLASS\nYour student's drop date will be scheduled for the final day of a calendar month only. Mid-month withdrawals are not permitted. Refund/credit for the remaining weeks in a paid month will not be issued once payment for that month has been processed. (e.g. if a student chooses to drop before the end of the paid month, tuition will not be prorated, credited, or refunded).\n​Important to note:\n* If you set your student's drop date for next month, your deposit will be applied toward your final month's class fees.\n* If you are withdrawing at the end of this current month, you will forfeit your non-refundable deposit.\n[MONTH-END DROP](https://www.museoartacademy.com/student-resources)\n​\n​\nPROGRAMS CALENDAR\nclasses and camps\n​\nWeekly classes run throughout the year with exception of the dates listed below. Classes DO NOT PAUSE for other school breaks or holidays.\n​No Classes On:​​​​​​\n* 05/24/25 - 05/26/25 Memorial Day weekend\n* 07/04/25 - 07/06/25 4th of July weekend\n* 08/30/25 - 09/01/25 Labor Day weekend\n* 11/27/25 - 11/30/25 Thanksgiving weekend\n* 12/22/25 - 01/04/26 WINTER BREAK\n![2025 03](https://static.wixstatic.com/media/d1b711_ae4ace50c245419aafa7debe167c039d~mv2.png/v1/fill/w_448,h_506,al_c,q_85,usm_0.66_1.00_0.01,enc_avif,quality_auto/Screenshot%20(649).png)\n![2025 04](https://static.wixstatic.com/media/d1b711_d1a56bfbbda54f0a80abd182b71faa08~mv2.png/v1/fill/w_448,h_440,al_c,q_85,usm_0.66_1.00_0.01,enc_avif,quality_auto/Screenshot%20(639).png)\n![2025 05](https://static.wixstatic.com/media/d1b711_102ba32a72ba49a7a6cfa07c6403a053~mv2.png/v1/fill/w_448,h_439,al_c,q_85,usm_0.66_1.00_0.01,enc_avif,quality_auto/Screenshot%20(640).png)\n![2025 06](https://static.wixstatic.com/media/d1b711_4c0c5fbdfcd84abab97d37203d8e793f~mv2.png/v1/fill/w_446,h_441,al_c,q_85,usm_0.66_1.00_0.01,enc_avif,quality_auto/Screenshot%20(641).png)\n![2025 07](https://static.wixstatic.com/media/d1b711_baf7cea3a0124feab143e1f31390d3d3~mv2.png/v1/fill/w_448,h_440,al_c,q_85,usm_0.66_1.00_0.01,enc_avif,quality_auto/Screenshot%20(642).png)\n![ 2025 08](https://static.wixstatic.com/media/d1b711_2a2e3bef73414a04a001cdda579a0141~mv2.png/v1/fill/w_448,h_501,al_c,q_85,usm_0.66_1.00_0.01,enc_avif,quality_auto/Screenshot%20(648).png)\n![2025 09](https://static.wixstatic.com/media/d1b711_c3a7253d426445408b400ef613aba45b~mv2.png/v1/fill/w_447,h_441,al_c,q_85,usm_0.66_1.00_0.01,enc_avif,quality_auto/Screenshot%20(644).png)\n![2025 11](https://static.wixstatic.com/media/d1b711_b075da5eda5646e58e22d3b6a0335867~mv2.png/v1/fill/w_447,h_506,al_c,q_85,usm_0.66_1.00_0.01,enc_avif,quality_auto/Screenshot%20(627).png)\n![2025 10](https://static.wixstatic.com/media/d1b711_ddcfdf165154462a881b62a4cc8b5fab~mv2.png/v1/fill/w_448,h_438,al_c,q_85,usm_0.66_1.00_0.01,enc_avif,quality_auto/Screenshot%20(645).png)\n![2025 12](https://static.wixstatic.com/media/d1b711_c148acc08b3747cd848eddd746355be7~mv2.png/v1/fill/w_448,h_440,al_c,q_85,usm_0.66_1.00_0.01,enc_avif,quality_auto/Screenshot%20(647).png)\n##### Pick-Up Permission\nUtilize this form to grant someone permission to pick up your student.\nNOTE: Parent submitting this form MUST be listed on the MUSEO account.\nStudent (s)\nMay be picked up by\nSelect an option\nAlways\nOn specific date(s) listed in comments below\nComment\nParent Authorizaton\nParent's Email\nParent's Mobile Phone\nI accept terms & conditions\nSubmit Request\nThank you. Please allow two business days (M-F) to process.\n##### Permission to Leave Without Sign-Out\nNOTE: The parent submitting this form MUST be listed on the MUSEO account.\nStudent (s)\nMy student may leave the classroom without sign-out...\nSelect an option \\*\nEach week from class\nOn specific date(s) listed in comments below\nComment\nAuthorizing Parent\nParent's Email\nParent's Mobile Phone\nI accept terms & conditions\nSubmit Request\nThank you. Please allow two business days (M-F) to process.\n##### Curbside Pick-Up\nNOTE: The parent submitting this form MUST be listed on the MUSEO account.\nStudent (s)\nPlease bring my student downstairs for curbside pick-up...\nSelect an option \\*\nEach week from class\nOn specific date(s) listed in comments below\nComment\nAuthorizing Parent\nParent's Email\nParent's Mobile Phone\nI accept terms & conditions\nSubmit Request\nThank you. Please allow two business days (M-F) to process.\n[Glazing Sessions](https://www.museoartacademy.com/glazing-sessions)\n[Yelp Promo](https://www.museoartacademy.com/free-trial-ad-yelp)\n[Google Promo](https://www.museoartacademy.com/ad-google)\n[Registration Received](https://www.museoartacademy.com/registration-received)\n[Purple Shirt Challenge](https://www.museoartacademy.com/purple-shirt-challenge)\n[Summer Camps Peachjar Flyer](https://www.museoartacademy.com/summer-camps-peachjar)\n[Summer Camps IG Ad](https://www.museoartacademy.com/summer-camps-instagram)\n© 2006 - 2025 MUSEO Art Academy & Gallery. All Rights Reserved.\nbottom of page</markdown>\n<label>r/onepiece</label>\n<dataType>markdown</dataType>\n",
            ]
        ]
        webpage_markdown_input_data_participants = ["UNKNOWN_SPEAKER"]
        webpage_markdown_input_data_total = 1

        webpage_tagging_task = WebpageMetadataGenerationTaskBundle(
            mode="local",
            type="webpage_metadata_generation",
            guid=webpage_tagging_task_guid,
            scoring_mechanism="ground_truth_tag_similarity_scoring",
            input=WebpageMarkdownInput(
                input_type="webpage_markdown",
                guid=webpage_tagging_task_guid,
                data=WebpageMarkdownInputData(
                    lines=webpage_markdown_input_data_lines,
                    participants=webpage_markdown_input_data_participants,
                    total=webpage_markdown_input_data_total,
                ),
            ),
            prompt_chain=[
                PromptChainStep(
                    step=0,
                    id="12346546888",
                    crc=1321321,
                    title="Infer the tags of the web page from the provided Markdown",
                    name="infer_tags_for_webpage_from_markdown",
                    description="Returns tags representing the webpage from the content of the page in Markdown.",
                    type="inference",
                    input_path="markdown",
                    prompt_template="You are given the content of a webpage inside <markdown>...</markdown> tags. Identify the most relevant high-level topics, entities, and concepts that describe the page. Focus only on the core subject matter and ignore navigation menus, boilerplate, or contact info. Return only a flat list of tags in lowercase, separated by commas, with no explanations, formatting, or extra text. Example of required format: tag1, tag2, tag3",
                    output_variable="final_output",
                    output_type="List[str]",
                )
            ],
            example_output=TaggingExampleOutput(tags=["guitar", "barn", "farm", "nashville"], type="List[str]"),
            errors=[],
            warnings=[],
            data_type=1,
        )

        conversation_tagging_task = ConversationTaggingTaskBundle(
            mode="local",
            type="conversation_tagging",
            guid=convo.get("guid"),
            scoring_mechanism="ground_truth_tag_similarity_scoring",
            input=ConversationInput(
                input_type="conversation",
                guid=convo.get("guid"),
                data=ConversationInputData(
                    total=len(convo.get("lines")),
                    participants=convo.get("participants"),
                    lines=convo.get("lines"),
                ),
            ),
            prompt_chain=[
                PromptChainStep(
                    step=0,
                    id="12346546888",
                    crc=1321321,
                    title="Infer tags from a conversation window",
                    name="infer_tags_from_a_conversation_window",
                    description="Returns tags representing the conversation as a whole from the window received.",
                    type="inference",
                    input_path="conversation",
                    prompt_template="Analyze conversation in terms of topic interests of the participants. Analyze the conversation (provided in structured XML format) where <p0> has the questions and <p1> has the answers. Return comma-delimited tags. Only return the tags without any English commentary.",
                    output_variable="final_output",
                    output_type="List[str]",
                )
            ],
            example_output=TaggingExampleOutput(tags=["guitar", "barn", "farm", "nashville"], type="List[str]"),
            errors=[],
            warnings=[],
            data_type=1,
        )

        choice = random.choice([webpage_tagging_task, conversation_tagging_task])
        # choice = random.choice([webpage_tagging_task])
        print(f"Selected task: {choice.type} with GUID {choice.guid}")

        return choice

    except Exception as e:
        print(f"Error: {e}")
        return {
            "mode": "error",
            "api_version": 1.4,
            "type": "unknown",
            "scoring_mechanism": None,
            "input": None,
            "prompt_chain": [],
            "example_output": None,
            "errors": [f"post_request failed: {str(e)}"],
            "warnings": [],
            "guid": "ERROR",
            "total": 0,
            "participants": [],
            "lines": [],
            "min_convo_windows": 0,
        }


@app.put("/api/v1/conversation/record/{c_guid}")
def put_record_request(c_guid, data: dict):
    out = {"success": 0, "errors": [], "data": {}}
    if data:
        db_name = os.path.join(os.path.dirname(__file__), 'cgp_tags')
        db = Db(db_name, "tags")
        db.insert_into_table(c_guid, data)
        out['data']['msg'] = {"message": f"Stored tag data for {c_guid}"}
        out['success'] = 1
    else:
        out['errors'].append(
            [
                9893843,
                "Missing hotkey",
            ]
        )
    return out


@app.get("/metrics")
def metrics(request: Request):
    if request.client.host != "127.0.0.1":
        return Response(status_code=403)
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
