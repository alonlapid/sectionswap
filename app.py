from flask import Flask, flash, redirect, render_template,request, url_for,make_response,session
import pandas as pd
import pyodbc
import json
from pandas import read_sql


app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

@app.route('/')
def home():
    if not session.get('logged_in'):
        return render_template('login3.html')
    else:
        return selectshow()

@app.route('/login', methods=['POST'])
def do_login():
    try:  
        connect(request.form['username'], request.form['password'] )
        session['logged_in'] = True
        session['username'] = request.form['username']
        session['password'] = request.form['password']
        return selectshow()
    except Exception as e:       
        return render_template('login2.html',error=e)

@app.route('/logout')
def logout():
    session['logged_in'] = False
    return home()


@app.route('/swaprequest')
def swaprequest():
    con = connect(session['username'] ,session['password'])        
    enrolledsections = read_sql("select STR(SECID) + ' - ' + SEctionName as SECID from fn_enrollment() ",con)   
    allsections = read_sql("select STR(SECID) + ' - ' + Name as SECID from fn_section() where SECID not in ( select SECID   from fn_enrollment() ) and Course not in  ( select CID   from fn_credit() )",con)
    session['enrolledsections'] = enrolledsections.to_dict(orient='records')
    session['allsections'] = allsections.to_dict(orient='records')  
    df = read_sql("select * from fn_exchangerequest() ",con)
    if(len(df.index) == 0):
        session['pending'] = None
    else:
        session['pending'] = df.to_html(header="true", table_id="myTable")
    return render_template('swaprequest.html',data=session['enrolledsections'],data2=session['allsections'],pending=session['pending'])



@app.route('/test')
def test():
    return render_template('selectshow2.html')

@app.route('/swap',methods=['POST'])
def do_swap():
    if(not session['logged_in']):
        return home()

    con = connect(session['username'] ,session['password'])  
    cursor = con.cursor()   
    cursor.execute("sp_swap")
    cursor.commit() 
    session['matches'] = getmatches()
    return render_template('selectshow.html',matches=session['matches'], isadmin=session['isadmin'])      


@app.route('/cancel',methods=['POST'])
def do_cancel():
    if(not session['logged_in']):
        return home()

    if(request.method == 'POST'):
        con = connect(session['username'] ,session['password'])  
        cursor = con.cursor()   
        cursor.execute("sp_cancel_request_student")
        cursor.commit()   
        session['pending'] = None
        return render_template('swaprequest.html',data=session['enrolledsections'],data2=session['allsections'] )


@app.route('/request',methods=['POST'])
def do_request():
    if(not session['logged_in']):
        return home()

    if(request.method == 'POST'):
        drop = request.form.get('sectiontodrop') 
        add =  request.form.get('sectiontojoin') 
        sqlstmt = " sp_exchange_request_student " + drop.split('-')[0] + "," + add.split('-')[0]
        con = connect(session['username'] ,session['password'])  
        cursor = con.cursor()     
        try:    
            cursor.execute(sqlstmt)
            cursor.commit()   
            info = " The request to swap section " + drop + " for  section " + add + " was queued "   
            df = read_sql("select * from fn_exchangerequest() ",con)
            if(len(df.index) == 0):
                session['pending'] = None
            else:
                session['pending'] = df.to_html(header="true", table_id="myTable")

            return render_template('swaprequest.html',data=session['enrolledsections'],data2=session['allsections'],info=info,pending=session['pending'] )
        except Exception as e:
            return render_template('swaprequest.html',data=session['enrolledsections'],data2=session['allsections'],pending=session['pending'],info=sqlstmt + " " + str(e))    

@app.route('/selectshow') 
def selectshow():
    session['matches'] = getmatches()
    session['isadmin'] =isAdmin()
    return render_template('selectshow.html',matches=session['matches'],isadmin=session['isadmin']  )


def isAdmin():
    con = connect(session['username'] ,session['password'])  
    df = read_sql(" select IS_ROLEMEMBER ('db_owner') as isadmin ",con)
    return int(df['isadmin'][0])


def getmatches():
        con = connect(session['username'] ,session['password'])  
        df = read_sql(" select * from fn_match() ",con)
        if(len(df.index) == 0):
            return None
         
        return df.to_html(header="true", table_id="myTable") 


@app.route('/show', methods=['GET','POST'])
def show():
    entity={"sections":"fn_section()","courses":"fn_course()","students":"fn_student()","requests":"fn_exchangerequest()","enrollments":"fn_enrollment()","matches":"fn_match()","lessons":"fn_lesson()","credits":"fn_credit()","prereqs":"fn_prerequisite()","schedule":"fn_schedule_student()"}
    
    if(not session['logged_in']):
        return home()

    if(request.method == 'POST'):
        table = entity[request.form.get('entity') ]
        con = connect(session['username'] ,session['password'])
        filter=request.form.get('filter')
        sql = "select * from " + table
        if(filter and "sql filter" not in filter):
            sql = sql + " where " + filter

        try:    
            df = read_sql(sql,con)
            html = df.to_html(header="true", table_id="myTable")
            return render_template('selectshow.html',text=html,selected=request.form.get('entity'),filter=filter,matches=session['matches'],isadmin=session['isadmin'])
        except Exception as e:
            return render_template('selectshow.html',text="",selected=request.form.get('entity'),filter=filter,error=e,matches=session['matches'],isadmin=session['isadmin'])  
    else:
        return redirect(url_for('selectshow'))


def connect(username,password):   
    server = 'tcp:syncservercs133.database.windows.net' 
    database = 'courseswap' 
    return pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER='+server+';DATABASE='+database+';UID='+username+';PWD='+ password)

def run():
    app.run(debug=True, port=5690, host="0.0.0.0")

if __name__ == "__main__":
    run()    