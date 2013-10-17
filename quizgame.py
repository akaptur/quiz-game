import sqlite3
from contextlib import closing
from random import shuffle
from flask import Flask, render_template, request, redirect, g
from access_db import create_database, add_question

database = 'quizgame.db'
schema = 'schema.sql'

app = Flask(__name__)
app.config.from_object(__name__)

def connect_db():
    return sqlite3.connect(database)

def get_db_size():
    with closing(connect_db()) as conn:   
        try:
            sizeinfo = conn.execute("SELECT count(*) FROM questions")
            size = sizeinfo.fetchone()[0]
        except sqlite3.OperationalError:
            size = 0

    return size

def get_question(n):
    with closing(connect_db()) as db:
        cur = db.execute("SELECT question, ans1, ans2, ans3, ans4, correct FROM questions WHERE id=?", (n,))
        entry = cur.fetchall()[0]
        return dict(question=entry[0], A=entry[1], B=entry[2], C=entry[3],\
                    D=entry[4], correct=entry[5])

def get_questions(n):
    total_questions = get_db_size()
    question_nums = range(1, total_questions + 1)
    shuffle(question_nums)
    questions = []
    for i in range(n):
        question = get_question(question_nums[i])
        questions.append(question)
    return questions

def add_to_highscores(name, score):
    with closing(connect_db()) as db:
        try:
            db.execute("INSERT INTO highscores (name, score) VALUES (?, ?)", \
                           (name, score))
        except sqlite3.OperationalError:            
            db.execute("CREATE TABLE highscores (name, score)")
            db.execute("INSERT INTO highscores (name, score) VALUES (?, ?)", \
                           (name, score))

def get_highscores(num):
    with closing(connect_db()) as db:
        try:
            query = db.execute("SELECT score FROM highscores order by score")
            highscores = [(row[0], row[1]) for row in query.fetchall()]
            if len(highscores) < num:
                return highscores
            else:
                return highscores[:num+1]
        except sqlite3.OperationalError:
            return []
    
@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        total_questions = get_db_size()
        options = range(5, total_questions + 1, 5)

        if options[-1] != total_questions:
            options.append(total_questions)

        return render_template('welcome.html', options=options)

    else:
        nquestions = int(request.form['nquestions'])
        app.questions = get_questions(nquestions)
        app.nquestions = nquestions
        app.curquestion = 0
        app.score = 0
        app.highscores = get_highscores(10)
        if app.highscores:
            app.lowest_highscore = app.highscores[-1][1]
        else:
            app.lowest_highscore = None
        
        return redirect('main')

@app.route('/main')
def main():
    if app.curquestion >= app.nquestions:
        return redirect('/end')
    else:
        return redirect('/next')

@app.route('/end', methods=['GET','POST'])
def end():
    score = app.score/app.nquestions * 100
    #score = 100
    #app.lowest_highscore = None
    #app.highscores = get_highscores(10)
    if request.method == 'GET' and score > app.lowest_highscore:
        return render_template('end.html', score=score, \
                                   highscores=app.highscores, get_info=True)
    elif request.method == 'POST':
        name = request.form['name']
        add_to_highscores(name, score)
        # update highscores
        app.highscores = get_highscores(10)
        print app.highscores
        return render_template('end.html', score=score, \
                                   highscores=app.highscores, get_info=False)
        
    else:
        return render_template('end.html', score=score, \
                                   highscores=app.highscores, get_info=False)

@app.route('/next', methods=['GET', 'POST'])
def next():
    if request.method == 'GET':
        app.question_info = app.questions[app.curquestion]
        app.n = app.curquestion + 1
        app.q = app.question_info['question']
        a1, a2, a3, a4 = app.question_info['A'], app.question_info['B'], \
                         app.question_info['C'], app.question_info['D']
        
        return render_template('layout.html', num=app.n, question=app.q, \
                                   ans1=a1, ans2=a2, ans3=a3, ans4=a4)
    else:
        # gets response to question and stays on question if not answered
        ans = request.form
        if len(ans) == 0:
            return redirect('main')
        else:
            ans = ans['response']
            
        correct = app.question_info['correct']
        if ans == correct:
            app.score += 1.0
            feedback = 'Correct!'
        else:
            feedback = 'Incorrect! The correct answer was "%s"' \
                         %(app.question_info[correct])
        
        app.curquestion += 1

        return render_template('feedback.html', feedback=feedback, \
                                   question=app.q, num=app.n)


if __name__ == '__main__':
    if get_db_size() == 0:
        create_database(database, schema)
    app.run(debug=True)