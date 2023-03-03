import spacy, fitz,io
from flask import  session,request
from database import mongo
from bson.objectid import ObjectId
from MediaWiki import get_search_results


resumeFetchedData = mongo.db.resumeFetchedData
JOBS = mongo.db.JOBS


###Spacy model
print("Loading Jd Parser model...")
jd_model = spacy.load('assets/JdModel/output/model-best')
print("Jd Parser model loaded")




def Matching():
    job_id = request.form['job_id']
    jd_data = JOBS.find_one({"_id":ObjectId(job_id)},{"FileData":1})["FileData"]
    with io.BytesIO(jd_data) as data:
        doc = fitz.open(stream=data)
        text_of_jd = " "
        for page in doc:
            text_of_jd = text_of_jd + str(page.get_text())


    label_list_jd=[]
    text_list_jd = []
    dic_jd = {}

    doc_jd = jd_model(text_of_jd)
    for ent in doc_jd.ents:
        label_list_jd.append(ent.label_)
        text_list_jd.append(ent.text)

    print("Model work done")

    for i in range(len(label_list_jd)):
        if label_list_jd[i] in dic_jd:
            # if the key already exists, append the new value to the list of values
            dic_jd[label_list_jd[i]].append(text_list_jd[i])
        else:
            # if the key does not exist, create a new key-value pair
            dic_jd[label_list_jd[i]] = [text_list_jd[i]]

    print("Jd dictionary:",dic_jd)
    resume_workedAs = resumeFetchedData.find_one({"UserId": ObjectId(session['user_id'])}, {"WORKED AS": 1})["WORKED AS"]
    print("resume_workedAs: ",resume_workedAs)

    resume_experience_list = resumeFetchedData.find_one({"UserId": ObjectId(session['user_id'])}, {"YEARS OF EXPERIENCE": 1})["YEARS OF EXPERIENCE"]
    print("resume_experience: ",resume_experience_list)
    resume_experience = []
    for p in resume_experience_list:
        parts = p.split()
        if "years" in p or "year" in p:
            year = int(parts[0])
            if "months" in p or "month" in p:
                year += int(parts[2]) / 12
        else:
            year = int(parts[0]) / 12
        year = round(year, 2)
        resume_experience.append(year)

    print("resume_experience: ",resume_experience)

    resume_skills = resumeFetchedData.find_one({"UserId": ObjectId(session['user_id'])}, {"SKILLS": 1})["SKILLS"]
    print("resume_skills: ",resume_skills)

    job_description_skills = dic_jd.get('SKILLS')
    print("job_description_skills: ",job_description_skills)
    jd_experience_list = dic_jd.get('EXPERIENCE')
    print("jd_experience_list: ",jd_experience_list)
    jd_experience = []
    for p in jd_experience_list:
        parts = p.split()
        if "years" in p or "year" in p:
            year = int(parts[0])
            if "months" in p or "month" in p:
                year += int(parts[2]) / 12
        else:
            year = int(parts[0]) / 12
        year = round(year, 2)
        jd_experience.append(year)

    print("jd_experience: ",jd_experience)
    jd_post = dic_jd.get('JOBPOST')
    print("jd_post: ",jd_post)

    ###########################################################
    #########  Compare resume_workedAs and jd_post
    jd_post = [item.lower() for item in jd_post]
    experience_similarity = 0
    match_index = -1
    jdpost_similarity = 0
    if resume_workedAs:
        resume_workedAs = [item.lower() for item in resume_workedAs]
    
        for i, item in enumerate(resume_workedAs):
            if item in jd_post:
                result = True
                match_index = i
                ########   compare resume_experience and jd_experience
                if resume_experience:
                    experience_difference = (jd_experience[0] - resume_experience[match_index])
                    if (experience_difference <= 0):
                        print("Experience Matched")
                        experience_similarity = 1
                    elif (0 < experience_difference <= 1):
                        print("Experience  can be considered")
                        experience_similarity = 0.7
                    else:
                        print("Experience  Unmatched")
                        experience_similarity = 0
                
                    break
            else:
                result = False
                
        if result == True:
            jdpost_similarity = 1
        else:
            jdpost_similarity = 0

    jdpost_similarity = jdpost_similarity * 0.3
    print("jd_post_simiarity: ", jdpost_similarity)
    experience_similarity = experience_similarity * 0.2
    print("Experiece Similarity: ", experience_similarity)



    ########   compare resume_skills and jd_skills

    new_resume_skills = []
    count = 0
    if resume_skills:
        for skills in resume_skills:   
            search_query = f"{skills} in technology "
            results = get_search_results(search_query)
            if results:
                new_resume_skills.append(results) 
            else:
                print("No matching articles found")

    if job_description_skills:
        for skill in job_description_skills:
            for resume_skill in new_resume_skills:
                if skill in resume_skill:
                    count += 1
                    break

        skills_similarity =1 - ((len(job_description_skills) - count)/ len(job_description_skills))
        skills_similarity = skills_similarity * 0.5
        print("SKills Matched", skills_similarity)
    else:
        skills_similarity = 0
        print("SKills Matched", skills_similarity)

    matching=(jdpost_similarity+experience_similarity+skills_similarity)*100
    matching = round(matching,2)
    print("Overall Similarity between resume and jd is ",matching )

    return matching;



