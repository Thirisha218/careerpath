-- CareerPath core schema (MySQL 8). All seed rows are SAMPLE DATA, verify before real use.
CREATE DATABASE IF NOT EXISTS careerpath CHARACTER SET utf8mb4;
USE careerpath;
CREATE TABLE users(id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(80) NOT NULL, email VARCHAR(120) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL, role ENUM('student','admin') NOT NULL DEFAULT 'student', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE student_profiles(user_id INT PRIMARY KEY, stream ENUM('Science','Commerce','Arts','Other') NOT NULL,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE categories(id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(60) NOT NULL UNIQUE, icon VARCHAR(8) NOT NULL);
CREATE TABLE courses(id INT AUTO_INCREMENT PRIMARY KEY, category_id INT NOT NULL, name VARCHAR(120) NOT NULL, duration_years DECIMAL(3,1) NOT NULL,
  eligibility VARCHAR(255) NOT NULL, description TEXT NOT NULL, official_url VARCHAR(255) NULL,
  FOREIGN KEY(category_id) REFERENCES categories(id), INDEX idx_course_cat(category_id), INDEX idx_course_name(name));
CREATE TABLE careers(id INT AUTO_INCREMENT PRIMARY KEY, category_id INT NOT NULL, title VARCHAR(120) NOT NULL, summary TEXT NOT NULL,
  skills VARCHAR(255) NOT NULL, scope TEXT NOT NULL, roadmap TEXT NOT NULL COMMENT 'one step per line',
  FOREIGN KEY(category_id) REFERENCES categories(id), INDEX idx_career_cat(category_id));
CREATE TABLE assessments(id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL, scores JSON NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE, INDEX idx_assess_user(user_id, created_at));
CREATE TABLE saved_courses(user_id INT NOT NULL, course_id INT NOT NULL, PRIMARY KEY(user_id, course_id),
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE, FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE);
CREATE TABLE scholarships(id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(120) NOT NULL, eligibility VARCHAR(255) NOT NULL, official_url VARCHAR(255) NULL);

INSERT INTO categories(name,icon) VALUES('Technology','💻'),('Healthcare','🩺'),('Business','📊'),('Creative Arts','🎨');
INSERT INTO courses(category_id,name,duration_years,eligibility,description) VALUES
(1,'B.E./B.Tech Computer Science',4,'12th with Maths + Physics (sample)','Core programming, data structures, systems and software engineering.'),
(1,'BCA',3,'12th any stream, Maths preferred (sample)','Application development and computing fundamentals.'),
(2,'MBBS',5.5,'12th with PCB, NEET (sample)','Medical degree leading to practice as a doctor.'),
(2,'B.Sc Nursing',4,'12th with PCB (sample)','Clinical nursing training and patient care.'),
(3,'BBA',3,'12th any stream (sample)','Management, marketing and finance foundations.'),
(3,'B.Com',3,'12th, Commerce preferred (sample)','Accounting, taxation and business law.'),
(4,'B.Des',4,'12th any stream, design aptitude test (sample)','Design thinking, visual communication, product design.'),
(4,'BA Journalism & Mass Communication',3,'12th any stream (sample)','Reporting, media production and communication.');
INSERT INTO careers(category_id,title,summary,skills,scope,roadmap) VALUES
(1,'Software Developer','Builds web, mobile and backend software.','Programming, Problem solving, Databases','Strong demand across startups and IT services (sample).','Learn one language well\nBuild 3 small projects\nPick a degree: B.E. CSE or BCA\nIntern in 2nd/3rd year\nApply for fresher roles'),
(1,'Data Analyst','Turns data into decisions with charts and reports.','Excel, SQL, Statistics, Visualization','Needed in every industry (sample).','Strengthen Maths/Statistics\nLearn Excel and SQL\nLearn Python or R\nBuild a portfolio of analyses\nApply for analyst internships'),
(2,'Doctor','Diagnoses and treats patients.','Biology, Empathy, Patience','Long training, stable demand (sample).','Take PCB in 12th\nPrepare for NEET\nComplete MBBS\nInternship year\nOptional postgraduate specialization'),
(2,'Nurse','Provides clinical care and patient support.','Clinical skills, Communication','Hospitals and clinics hire continuously (sample).','Take PCB in 12th\nJoin an approved nursing program\nClinical training\nRegister with the nursing council\nApply to hospitals'),
(3,'Chartered Accountant','Handles audit, tax and financial reporting.','Accounting, Law, Detail orientation','Respected profession with steady demand (sample).','Register for CA foundation after 12th\nComplete intermediate\nArticleship training\nFinal exams\nPractice or join a firm'),
(3,'Marketing Manager','Plans campaigns and grows a brand.','Communication, Analytics, Creativity','Growing digital marketing roles (sample).','Choose BBA/B.Com/any degree\nLearn digital marketing basics\nIntern at an agency\nBuild a campaign portfolio\nApply for executive roles'),
(4,'UX Designer','Designs how apps and websites feel and work.','Design thinking, Prototyping, Research','Demand in product companies (sample).','Learn design basics\nPractice in Figma\nChoose B.Des or a related degree\nBuild 3 case studies\nApply for design internships'),
(4,'Journalist','Researches and reports stories across media.','Writing, Research, Ethics','Digital media is expanding (sample).','Read and write daily\nChoose a journalism degree\nStart a blog or channel\nIntern at a newsroom\nApply as a reporter');
INSERT INTO scholarships(name,eligibility) VALUES('Sample Merit Scholarship','Above 85% in 12th (sample)'),('Sample Need-Based Scholarship','Family income below limit (sample)'),('Sample Girls in STEM Grant','Girls entering Science/Tech degrees (sample)');
