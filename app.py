from flask import Flask, render_template, url_for, request, session, redirect, abort, jsonify
from database import mongo
from werkzeug.utils import secure_filename
import os,re
import spacy, fitz,io
from bson.objectid import ObjectId
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests
import pathlib
import requests




def allowedExtension(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ['docx','pdf']

def allowedExtensionPdf(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ['pdf']


   

app = Flask(__name__)


app.secret_key = "Resume_screening"
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
GOOGLE_CLIENT_ID = "Your Google Client ID here"
client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "client_secret.json") #verify this
flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],
    redirect_uri="http://127.0.0.1:5000/callback"
)






UPLOAD_FOLDER = 'static/uploaded_resumes'
app.config['UPLOAD_FOLDER']=UPLOAD_FOLDER

app.config['MONGO_URI']= 'Your Mongo URI here'


mongo.init_app(app)
resumeFetchedData = mongo.db.resumeFetchedData
Applied_EMP=mongo.db.Applied_EMP
IRS_USERS = mongo.db.IRS_USERS
JOBS = mongo.db.JOBS
resume_uploaded = False
from Job_post import job_post
app.register_blueprint(job_post,url_prefix="/HR1")

###Spacy model
print("Loading Resume Parser model...")
nlp = spacy.load('assets/ResumeModel/output/model-best')
print("Resune Parser model loaded")


@app.route('/')
def index():
    return render_template("index.html")

@app.route('/emp')
def emp():
    if 'user_id' in session and 'user_name' in session:
        return render_template("EmployeeDashboard.html")
    else:
        return render_template("index.html", errMsg="Login First")

@app.route('/login')
def login():
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    return redirect(authorization_url)

@app.route("/callback")
def callback():
    flow.fetch_token(authorization_response=request.url)

    if not session["state"] == request.args["state"]:
        abort(500)  # State does not match!

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID
    )
    result = None
    result = IRS_USERS.find_one({"Email":id_info.get("email")},{"_id":1})
    if result == None:
        session['user_id'] = str(IRS_USERS.insert_one({"Name":id_info.get("name"),"Email":id_info.get("email"),"Google_id":id_info.get("sub")}).inserted_id)
        session['user_name'] = str(id_info.get("name"))
    else:
        session['user_id'] = str(result['_id'])
        session['user_name'] = str(id_info.get("name"))
    return redirect("/emp")



@app.route('/signup', methods=["POST"])
def signup():
    if request.method == 'POST':
        name = str(request.form.get('name'))
        email = str(request.form.get('email'))
        password = str(request.form.get('password'))
        status = None
        status = IRS_USERS.insert_one({"Name":name,"Email":email,"Password":password})
        if status == None:
            return render_template("index.html",errMsg="Problem in user creation check data or try after some time")
        else:
            return render_template("index.html",successMsg="User Created Successfully!")

@app.route("/logout")
def logout():
    session.pop('user_id',None)
    session.pop('user_name',None)
    return redirect(url_for("index"))

@app.route('/HR_Homepage', methods=['GET', 'POST'])
def HR_Homepage():
    return render_template("CompanyDashboard.html")
    
@app.route('/HR', methods=['GET', 'POST'])
def HR():
    if request.method == 'POST':
        # Get the user's response from the form
        response = request.form['response']

        # Check the user's response and route accordingly
        if response == "777":
            
            return render_template("CompanyDashboard.html")
        elif response == "111":
            return render_template("CompanyDashboard.html")
            

        else:
            message = "Incorrect Id. Try Again !! "
        return render_template('form.html', message=message)

            
    else:
        # Render the form template
        return render_template('form.html')
    


@app.route('/test')
def test():
    return "Connection Successful"




@app.route("/uploadResume", methods=['POST'])
def uploadResume():
    if 'user_id' in session and 'user_name' in session:
        try:
            file = request.files['resume']
            filename = secure_filename(file.filename)
            # print("Extension:",file.filename.rsplit('.',1)[1].lower())
            if file and allowedExtension(file.filename):
                temp = resumeFetchedData.find_one({"UserId":ObjectId(session['user_id'])},{"ResumeTitle":1})

                if temp == None:
                    print("HELLO")
                else:
                    print("hello")
                    resumeFetchedData.delete_one({"UserId":ObjectId(session['user_id'])})
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'],temp['ResumeTitle']))
                file.save(os.path.join(app.config['UPLOAD_FOLDER'],filename))
                print("Resume Uploaded")
                
                
                fname = "static/uploaded_resumes/"+filename
                print(fname)
                doc = fitz.open(fname)
                print("Resume taken as input")

                text_of_resume = " "
                for page in doc:
                    text_of_resume = text_of_resume + str(page.get_text())

                label_list=[]
                text_list = []
                dic = {}
                
                doc = nlp(text_of_resume)
                for ent in doc.ents:
                    label_list.append(ent.label_)
                    text_list.append(ent.text)
                
                print("Model work done")

                for i in range(len(label_list)):
                    if label_list[i] in dic:
                        # if the key already exists, append the new value to the list of values
                        dic[label_list[i]].append(text_list[i])
                    else:
                        # if the key does not exist, create a new key-value pair
                        dic[label_list[i]] = [text_list[i]]
                
                print(dic)
                resume_data_annotated = ''
                for key, value in dic.items():
                    for val in value:
                        resume_data_annotated += val + " "
               
                resume_name = dic.get('NAME')
                if resume_name is not None:
                    value_name = resume_name[0]
                else:
                    value_name = None

                resume_linkedin = dic.get('LINKEDIN LINK')
                if resume_linkedin is not None:
                    value_linkedin = resume_linkedin[0]
                    value_linkedin = re.sub('\n', '',value_linkedin)
                else:
                    value_linkedin= None


                resume_skills = dic.get('SKILLS')
                if resume_skills is not None:                  
                    value_skills = resume_skills
                else:
                    value_skills = None

                resume_certificate = dic.get('CERTIFICATION')
                if resume_certificate is not None:
                    value_certificate = resume_certificate
                else:
                    value_certificate=None

                resume_workedAs = dic.get('WORKED AS')
                if resume_workedAs is not None:
                    value_workedAs = resume_workedAs
                else:
                    value_workedAs = None
            

                resume_experience = dic.get('YEARS OF EXPERIENCE')
                if resume_experience is not None:
                    value_experience = resume_experience
                else:
                    value_experience = None
               
                
                result = None               
                result = resumeFetchedData.insert_one({"UserId":ObjectId(session['user_id']),"Name":value_name,"LINKEDIN LINK": resume_linkedin,"SKILLS": value_skills,"CERTIFICATION": value_certificate,"WORKED AS":value_workedAs,"YEARS OF EXPERIENCE":value_experience,"Appear":0,"ResumeTitle":filename,"ResumeAnnotatedData":resume_data_annotated,"ResumeData":text_of_resume})                
                
                if result == None:
                    return render_template("EmployeeDashboard.html",errorMsg="Problem in Resume Data Storage")  
                else:
                    return render_template("EmployeeDashboard.html",successMsg="Resume Screen Successfully!!")
            else:
                return render_template("EmployeeDashboard.html",errorMsg="Document Type Not Allowed")
        except:
            print("Exception Occured")
    else:
        return render_template("index.html", errMsg="Login First")


@app.route('/viewdetails', methods=['POST', 'GET'])
def viewdetails():      
    employee_id = request.form['employee_id']     
    result = resumeFetchedData.find({"UserId":ObjectId(employee_id)})     
    dt=result[0]
    name_resume=dt['Name']
    if name_resume is not None:
        name = name_resume
    else:
        name = None

    linkedin_link=dt['LINKEDIN LINK']
    if name_resume is not None:
        name = name_resume
    else:
        name = None

    skill_resume=dt['SKILLS']
    if skill_resume is not None:
        skills = skill_resume
    else:
        skills = None

    certificate_resume=dt['CERTIFICATION']
    if certificate_resume is not None:
        certificate = certificate_resume
    else:
        certificate = None

    return jsonify({'name':name,'linkedin_link':linkedin_link,'skills':skills,'certificate':certificate})


@app.route("/empSearch",methods=['POST'])
def empSearch():
    if request.method == 'POST':
        category = str(request.form.get('category'))
        print(category)
        
        TopEmployeers = None
        job_ids = []
        job_cursor = JOBS.find({"Job_Profile": category},{"_id": 1})
        for job in job_cursor:
            job_ids.append(job['_id'])

        TopEmployeers = Applied_EMP.find({"job_id": {"$in": job_ids}},{"user_id": 1, "Matching_percentage": 1}).sort([("Matching_percentage", -1)])
        # print(TopEmployeers)
        # print(type(TopEmployeers))
        if TopEmployeers == None:
            return render_template("CompanyDashboard.html",errorMsg="Problem in Category Fetched")
        else:
            selectedResumes={}
            cnt = 0

            for i in TopEmployeers:
                se=IRS_USERS.find_one({"_id":ObjectId(i['user_id'])},{"Name":1,"Email":1,"_id":1})
                selectedResumes[cnt] = {"Name":se['Name'],"Email":se['Email'],"_id":se['_id']}
                se = None
                cnt += 1
            print("len", len(selectedResumes))
            return render_template("CompanyDashboard.html",len = len(selectedResumes), data = selectedResumes)
           

if __name__=="__main__":
    app.run(debug=True)