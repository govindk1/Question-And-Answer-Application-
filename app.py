from flask import Flask, render_template, request, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user, fresh_login_required
from urllib.parse import urlparse, urljoin
import operator
import collections
import flask_whooshalchemyplus as wap
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from rake_nltk import Rake

app = Flask(__name__)
db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login' #when you need to log in it will redirect to the login
login_manager.login_message = 'You need to log in first!'

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root@localhost/iwpfinal'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['SECRET_KEY'] = '@adsasd#$'
app.config['WHOOSH_BASE'] = 'whoosh'




class User(UserMixin, db.Model):
	id = db.Column(db.Integer, primary_key = True)
	name = db.Column(db.String(50), nullable = False)
	password = db.Column(db.String(50), nullable = False)
	expert = db.Column(db.Integer)
	admin = db.Column(db.Integer)
	ask = db.relationship('Question', backref = 'owner')
	

class Question(db.Model):
	__searchable__ = ['question_text']

	id = db.Column(db.Integer, primary_key = True)
	question_text = db.Column(db.Text, nullable = False)
	tags = db.Column(db.Text)
	answer_text = db.Column(db.Text)
	asked_by_id = db.Column(db.Integer, db.ForeignKey('user.id')) #one-to-many relationship
	expert_id = db.Column(db.Integer)
	total_likes = db.Column(db.Integer, default = 0)
	total_dislikes = db.Column(db.Integer, default = 0)

	
wap.whoosh_index(app, Question)


class Lidi(db.Model):
	id = db.Column(db.Integer, primary_key = True)
	question_id = db.Column(db.Integer)
	likes = db.Column(db.Integer,  default = 0)
	dislikes = db.Column(db.Integer,  default = 0) #one-to-many relationship
	user_id = db.Column(db.Integer)

def is_safe_url(target):
	ref_url = urlparse(request.host_url) #breaks down local host into components <scheme>://<netloc>/<path>;<params>?<query>#<fragment>
	test_url = urlparse(urljoin(request.host_url, target))  #to join the url

	return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

@login_manager.user_loader  #used to reload the user object from the user ID stored in the session.
def load_user(user_id):
	return User.query.get(int(user_id))

#def get_current_user():
#	if 'user' in session:
#		user_result = User.query.filter_by(name = session['user']).first()
#		return user_result 



@app.route('/likes/<question_id>', methods=['GET','POST'])
@login_required
def like(question_id):
	user_info = Lidi.query.filter_by(question_id = question_id, user_id = current_user.id).first()

	if user_info:
		if(user_info.dislikes == 1):
			user_info.likes = 1
			user_info.dislikes = 0;
			db.session.commit()
		

	else:
		likes_info = Lidi(question_id = question_id, user_id = current_user.id, likes = 1)
		db.session.add(likes_info)
		db.session.commit()

	
	return redirect(url_for('index'))


@app.route('/dislikes/<question_id>', methods=['GET','POST'])
@login_required
def dislike(question_id):
	user_info = Lidi.query.filter_by(question_id = question_id, user_id = current_user.id).first()

	if user_info:
		if(user_info.likes == 1):
			user_info.dislikes = 1
			user_info.likes = 0;
			db.session.commit()
		

	else:
		dislikes_info = Lidi(question_id = question_id, user_id = current_user.id, dislikes = 1)
		db.session.add(dislikes_info)
		db.session.commit()

	
	return redirect(url_for('index'))


@app.route('/', methods = ['GET', 'POST'])
def index():
	#user = get_current_user()

	flag = 0
	result = Question.query.all()
	size = 0 
	for r in result:
		#calculating total likes and total dislikes
		total_calc = Lidi.query.filter_by(question_id = r.id).all()
		total_dislikes = 0
		total_likes = 0;
		for i in total_calc:
			total_likes += i.likes
			total_dislikes += i.dislikes

		r.total_likes = total_likes;
		r.total_dislikes = total_dislikes;
		db.session.commit()


	answer = []
	expert_name = []

	for r in result:
		if r.answer_text != None:
			result1 = User.query.filter_by(id = r.expert_id).first()
			expert_name.append(result1.name)		

	k = 0


	for r in result:
		if r.answer_text != None:
			tag_per_question = r.tags.split(',');
			answer.append(r.question_text)
			answer.append(r.owner.name)
			answer.append(expert_name[k])
			answer.append(r.id)
			answer.append(r.total_likes)
			answer.append(r.total_dislikes)

			if(len(tag_per_question) == 0):
				answer.append('');
				answer.append('');
				answer.append('');


			if(len(tag_per_question) == 1):
				answer.append(tag_per_question[0]);
				answer.append('');
				answer.append('');

			if(len(tag_per_question) == 2):
				answer.append(tag_per_question[0]);
				answer.append(tag_per_question[1]);
				answer.append('');

			if(len(tag_per_question) == 3):
				answer.append(tag_per_question[0]);
				answer.append(tag_per_question[1]);
				answer.append(tag_per_question[2]);

			k += 1



	size = int(len(answer)/9)
	#When a user is anonymous the current_user is set to AnonymousUserMixin
	
	if(current_user.is_anonymous == True): #checking whether the user is anonymous or not
		flag = 1

	if flag == 1:
		return render_template('home.html', user = None, answer = answer, size = size)

	return render_template('home.html', user = current_user, answer = answer, size = size)


@app.route('/increasing/<type_>', methods = ['GET', 'POST'])
def increasing(type_):
	#user = get_current_user()
	print('a',type_)

	flag = 0
	result = Question.query.all()

	answer = []
	expert_name = []


	key_value = {}

	for r in result:
		if r.answer_text != None:
			result1 = User.query.filter_by(id = r.expert_id).first()
			expert_name.append(result1.name)
			if r.total_dislikes == 0 and r.total_likes == 0:
				key_value[r] = 0
			else:
				key_value[r] = r.total_likes/(r.total_likes+r.total_dislikes);

	reverse_value = False
	if type_ == '1':
		reverse_value = True

	sorted_x = sorted(key_value.items(), key=operator.itemgetter(1), reverse = reverse_value)
	key_value = collections.OrderedDict(sorted_x)
	print(key_value)
	
	k = 0


	for r in key_value:
		if r.answer_text != None:
			answer.append(r.question_text)
			answer.append(r.owner.name)
			answer.append(expert_name[k])
			answer.append(r.id)
			answer.append(r.total_likes)
			answer.append(r.total_dislikes)

			k += 1



	size = int(len(answer)/6)
	#When a user is anonymous the current_user is set to AnonymousUserMixin
	
	if(current_user.is_anonymous == True): #checking whether the user is anonymous or not
		flag = 1

	if flag == 1:
		return render_template('home.html', user = None, answer = answer, size = size)

	return render_template('home.html', user = current_user, answer = answer, size = size)


@app.route('/register', methods = ['GET', 'POST'])
def register():
	if request.method == 'POST':

		existing_member = User.query.filter_by(name = request.form['name']).first()

		if existing_member:
			return render_template('register.html', error = "User already exist")


		user_info = User(name = request.form['name'], password = request.form['password'])
		db.session.add(user_info)
		db.session.commit()

		return redirect(url_for('index'))
	return render_template('register.html')


@app.route('/login', methods = ['GET', 'POST'])
def login():
	flag = 0
	#user = get_current_user()
	error = None
	if request.method == 'POST':
		check_credential = User.query.filter_by(name = request.form['name']).first()

		if check_credential: 
			if check_credential.password == request.form['password']:
				user = User.query.filter_by(name = request.form['name']).first()
				#session['user'] = request.form['name']
				login_user(user)
				if 'next' in session: #it stored the url of those page which requires login
					next = session['next'] #so after login we want to redirect to that page
					print(next)
					if is_safe_url(next) and next is not None: #we are checking whether it exists in same server
						return redirect(next)

				return redirect(url_for('index'))

			else:
				error = 'invalid username or password'

		else:
			error = 'invalid username or password'

	session['next'] = request.args.get('next')

	if(current_user.is_anonymous == True): #checking whether the user is anonymous or not
		flag = 1

	if flag == 1:
		return render_template('login.html', user = None, error = error)

	return render_template('login.html', user = current_user, error = error)


@app.route('/search', methods = ['GET', 'POST'])
@login_required
def search():

	

	if request.method == "POST":
		
		try:
			results = Question.query.whoosh_search(request.form["search"]).all()
		
		except:
			return render_template('search.html', size = 0, error = 'Not Found!!!', user = current_user)

		if results:
			answer = []
			expert_name = []

			for r in results:
				if r.answer_text != None:
					result1 = User.query.filter_by(id = r.expert_id).first()
					expert_name.append(result1.name)		

			k = 0


			for r in results:
				if r.answer_text != None:
					answer.append(r.question_text)
					answer.append(r.owner.name)
					answer.append(expert_name[k])
					answer.append(r.id)
					answer.append(r.total_likes)
					answer.append(r.total_dislikes)

					k += 1



			size = int(len(answer)/6)
			return render_template('search.html', user = current_user, answer = answer, size = size)
	

	return render_template('search.html', size = 0, user=current_user)


@app.route('/myfeed')
@login_required
def myfeed():

	if current_user.admin == 1 or current_user.expert == 1:
		if 'next' in session:  #since user trying to access the page which is not available for them and thus we redirect it to the home
			return redirect(url_for('index'))
		return redirect(url_for('login'))

	questions = current_user.ask
	compare_questions = Question.query.filter(Question.asked_by_id != current_user.id).all()
	
	result = []

	for i in questions:
		for j in compare_questions:
			
			X = i.question_text
			Y = j.question_text	

			# tokenization 
			X_list = word_tokenize(X)  
			Y_list = word_tokenize(Y)

			# sw contains the list of stopwords
			sw = stopwords.words('english')  
			l1 =[]
			l2 =[]

			# remove stop words from the string
			X_set = {w for w in X_list if not w in sw}  
			Y_set = {w for w in Y_list if not w in sw}  

			rvector = X_set.union(Y_set)  
			for w in rvector: 
			    if w in X_set: l1.append(1) # create a vector 
			    else: l1.append(0) 
			    if w in Y_set: l2.append(1) 
			    else: l2.append(0) 
			c = 0
  
			# cosine formula  
			for k in range(len(rvector)): 
			        c+= l1[k]*l2[k] 
			cosine = c / float((sum(l1)*sum(l2))**0.5) 


			if(cosine >= 0.5):
				expert_name = User.query.filter_by(id = j.expert_id).first()
				result.append(j.question_text)
				result.append(j.owner.name)
				result.append(expert_name.name)
				result.append(j.id)
				result.append(j.total_likes)
				result.append(j.total_dislikes)

	size = int(len(result)/6)


	return render_template('myfeed.html',user = current_user, size= size, answer = result)


@app.route('/ask', methods = ['GET', 'POST'])
@login_required
def ask():

	#user = get_current_user()

	#if not user or user.admin == 1 or user.expert == 1:
	if current_user.admin == 1 or current_user.expert == 1:
		if 'next' in session:  #since user trying to access the page which is not available for them and thus we redirect it to the home
			return redirect(url_for('index'))
		return redirect(url_for('login'))
	expert_list = User.query.filter_by(expert = 1).all()

	if request.method == 'POST':

		compare_questions = Question.query.all()		

		X = request.form['question'];

		r = Rake()
		r.extract_keywords_from_text(X)
		tags = r.get_ranked_phrases()

		if(len(tags) == 1):
			tags_sentence = tags[0]

		if(len(tags) == 2):
			tags_sentence = f'{tags[0]},{tags[1]}'

		elif(len(tags) > 2):
			tags_sentence = f'{tags[0]},{tags[1]},{tags[2]}'

		print(tags_sentence)
		
		for j in compare_questions:
				
			Y = j.question_text	

			# tokenization 
			X_list = word_tokenize(X)  
			Y_list = word_tokenize(Y)

			# sw contains the list of stopwords
			sw = stopwords.words('english')  
			l1 =[]
			l2 =[]

			# remove stop words from the string
			X_set = {w for w in X_list if not w in sw}  
			Y_set = {w for w in Y_list if not w in sw}  

			rvector = X_set.union(Y_set)  
			for w in rvector: 
				   if w in X_set: l1.append(1) # create a vector 
				   else: l1.append(0) 
				   if w in Y_set: l2.append(1) 
				   else: l2.append(0) 
			c = 0
	  
			# cosine formula  
			for k in range(len(rvector)): 
				c+= l1[k]*l2[k] 
				cosine = c / float((sum(l1)*sum(l2))**0.5) 


			if(cosine >= 0.95):
				return render_template('ask.html', user = current_user, expert_list = expert_list, error = 'Similar Type Of Question Is Already There.')


		expert_id1 = User.query.filter_by(name = request.form['expert']).first()
		test = Question(question_text = request.form['question'], tags = tags_sentence, asked_by_id = current_user.id, expert_id = expert_id1.id)
		db.session.add(test)
		db.session.commit()
		return redirect(url_for('index'))

	return render_template('ask.html', user = current_user, expert_list = expert_list)


@app.route('/answer/<question_id>', methods = ['GET', 'POST'])
@login_required
def answer(question_id):

	#user = get_current_user()

	#if not user  or user.expert == None:
	if current_user == None:
		if 'next' in session:
			return redirect(url_for('index'))
		return redirect(url_for('login'))

	question = Question.query.filter_by(id = question_id).first()


	if request.method == 'POST':
		print(request.form['answer'])
		question.answer_text = request.form['answer']
		db.session.commit()

		return redirect(url_for('index'))

	return render_template('answer.html', user = current_user, question = question)


@app.route('/unanswered')
@login_required
def unanswered():

	#user = get_current_user()


	#if not user or user.expert == None:
	if current_user.expert == None:
		if 'next' in session:
			return redirect(url_for('index'))
		return redirect(url_for('login'))

	expert_id = current_user.id 

	result = Question.query.filter_by(expert_id = expert_id).all()



	return render_template('unanswered.html', user = current_user, result = result)



@app.route('/question/<question_id>')
@login_required
def question(question_id):

	#user = get_current_user()



	answer = Question.query.filter_by(id = question_id).first()
	name = User.query.filter_by(id = answer.expert_id).first()
	return render_template('question.html', user = current_user, answer = answer, name = name)


@app.route('/myquestion')
@login_required
def myquestion():

	#user = get_current_user()

	#if not user or user.expert == 1:
	if current_user.expert == 1:
		if 'next' in session:
			return redirect(url_for('index'))
		return redirect(url_for('login'))
	res = current_user.ask

	answer = []

	for i in res:
		res1 = User.query.filter_by(id = i.expert_id).first()
		answer.append(i.id)
		answer.append(i.question_text)
		answer.append(res1.name)
		answer.append(i.answer_text)
		answer.append(i.total_likes)
		answer.append(i.total_dislikes)
		print(i.total_likes, i.total_dislikes)	


	print(answer)
	size = int(len(answer)/6)
	return render_template('myquestion.html', user = current_user, answer = answer, size = size)

@app.route('/users')
@login_required
def users():

	

	#user = get_current_user()

	#if not user or user.admin == None:
	if current_user.admin == None:
		if 'next' in session:
			return redirect(url_for('index'))
		return redirect(url_for('login'))

	list_of_user = User.query.all()
	return render_template('users.html',user = current_user, user_result = list_of_user)



@app.route('/promote/<user_id>')
@login_required
def promote(user_id):


	#user = get_current_user()

	#if not user or user.admin == None:
	if current_user.admin == None:
		if 'next' in session:
			return redirect(url_for('index'))
		return redirect(url_for('login'))

	res = User.query.filter_by(id = user_id).first()

	if(res.expert == 0):
		res.expert = 1

	else:
		res.expert = 0
	db.session.commit()

	return redirect(url_for('users'))

@app.route('/logout')
@login_required
def logout():

	#session.pop('user', None)
	logout_user() #destroys the session
	return redirect(url_for('index'))

if __name__ == '__main__':
	app.run(debug = True)