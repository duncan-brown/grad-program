#!/usr/local/bin/python

import sys
import re
from pdfreader import SimplePDFViewer

def parse_courses(course_strings, courses_taken, courses_in_progress, 
                  subject='PHY', 
                  valid_grades = ['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'F', 'NR']):

    six_ninety_done = 0
    six_ninety_in_progress = 0
    
    for s in course_strings:
        line = s.split('(' + subject)[1:]
        for l in line:
            line_data = l.split(')')
            course_number = line_data[0]
            credits = int(float(line_data[3].split('(',1)[1]))
            grade = line_data[4].split('(',1)[1].strip()
            if grade in valid_grades:
                if subject == 'PHY' and course_number == 690:
                    six_ninety_done += credits
                else:
                    courses_taken.add((subject + course_number,credits))
            else:
                if subject == 'PHY' and course_number == 690:
                    six_ninety_in_progress += credits
                else:
                    courses_in_progress.add((subject + course_number,credits))

    if six_ninety_done:
        courses_taken.add((690, six_ninety_done))

    if six_ninety_in_progress:
        courses_in_progress.add((690, six_ninety_in_progress))

    return courses_taken, courses_in_progress

def parse_student(markdown, current_semester):

    if len(re.findall('Undergrad', markdown)) > 0:
        return

    student_string = markdown.split('(Graduate Record)')[0]
    suid = re.findall(r'\([0-9]{5}-[0-9]{4}\)', markdown)[0][1:-1]
    print('Student {}'.format(suid))

    if len(re.findall('\(All But Dissertation\)', markdown)) > 0:
        print('Has ABD status')
        abd = True
    else:
        abd = False

    if len(re.findall('\(Qualifying Exam 1\)', markdown)) > 0:
        pass_wqe = True
    else:
        pass_wqe = False

    if len(re.findall('\(Qualifying Exam 2\)', markdown)) > 0:
        pass_research_oral = True
    else:
        pass_research_oral = False

    gpa_strings = re.findall(r'\(.*?\)',markdown.split(
        '(** Graduate Record Credit Summary **)', 1)[1].split(
        '(End of Graduate Record)')[0])

    for s in gpa_strings:
        desc, data = s.split(':')
        desc = desc[1:].strip()
        data = data[:-1].strip()
        if desc == 'Total Units Earned':
            credits_earned = int(float(data))
        if desc == 'Transfer Credit':
            credits_transfered = int(float(data))

    courses_taken = set()
    courses_in_progress = set()

    course_strings = markdown.split('-Physics)')
    courses_taken, courses_in_progress = parse_courses(course_strings, courses_taken, courses_in_progress)

    current_semester_string = markdown.split(current_semester + '-Physics)')[-1:]
    c = set()
    t = set()
    c, t = parse_courses(current_semester_string, c, t, 'PHY', 'NR')
    c, t = parse_courses(current_semester_string, c, t, 'GRD', 'NR')
    current_courses = c.union(t)

    required_core = {('PHY621',3), ('PHY641',3), ('PHY661',3), ('PHY662',3), ('PHY731',3)}

    if courses_taken.intersection(required_core) == required_core:
        print('Has completed required core courses')
        completed_core = True
    else:
        print('Needs to complete required core courses')
        completed_core = False

    required_lab = {('PHY514',3), ('PHY614',3), ('PHY651',3)}
    if len(courses_taken.intersection(required_lab)) > 0:
        print('Has completed required skills courses')
        completed_lab = True
    else:
        print('Needs to complete required skills courses')
        completed_lab = False

    elective_courses = { ('PHY607', 3),
                         ('PHY635', 3),
                         ('PHY638', 3),
                         ('PHY731', 3),
                         ('PHY750', 3),
                         ('PHY771', 3),
                         ('PHY785', 3),
                         ('PHY795', 3),
                         ('PHY831', 3),
                         ('PHY880', 3),
                         ('PHY885', 3),
                         ('PHY886', 3),
                         ('PHY890', 3),
                         ('PHY990', 3) }

    elective_credits = 3 * len(courses_taken.intersection(elective_courses))

    for c in courses_taken:
        course, credits = c
        if course == 'PHY690':
            elective_credits += credits

    if elective_credits > 8:
        print('Has completed elective courses')
        has_electives = True
    else:
        print('Needs to complete elective courses')
        has_electives = False

    missing_grades = courses_in_progress.difference(current_courses)

    print('Currently taking {}'.format(current_courses))
    if len(missing_grades):
        print('Missing grades for {}'.format(missing_grades))
    print('Total {} credits with {} transfer credits.'.format(credits_earned, credits_transfered))
    print('Needs {} more credits for ABD status.'.format(48 - credits_earned))

fd = open('Transcripts.PDF','rb')
viewer = SimplePDFViewer(fd)

all_pages = [p for p in viewer.doc.pages()]

for p in range(len(all_pages)):
    viewer.navigate(p+1)
    viewer.render()
    parse_student(viewer.canvas.text_content,'Fall 2020')

sys.exit(0)
