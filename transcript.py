#!/usr/local/bin/python

import sys
import re
import csv
from pdfreader import SimplePDFViewer
import logging
import argparse
import pandas as pd
import xlsxwriter

def addLoggingLevel(levelName, levelNum, methodName=None):
    """
    Comprehensively adds a new logging level to the `logging` module and the
    currently configured logging class.

    `levelName` becomes an attribute of the `logging` module with the value
    `levelNum`. `methodName` becomes a convenience method for both `logging`
    itself and the class returned by `logging.getLoggerClass()` (usually just
    `logging.Logger`). If `methodName` is not specified, `levelName.lower()` is
    used.

    To avoid accidental clobberings of existing attributes, this method will
    raise an `AttributeError` if the level name is already an attribute of the
    `logging` module or if the method name is already present 

    Example
    -------
    >>> addLoggingLevel('TRACE', logging.DEBUG - 5)
    >>> logging.getLogger(__name__).setLevel("TRACE")
    >>> logging.getLogger(__name__).trace('that worked')
    >>> logging.trace('so did this')
    >>> logging.TRACE
    5

    """
    if not methodName:
        methodName = levelName.lower()

    if hasattr(logging, levelName):
       raise AttributeError('{} already defined in logging module'.format(levelName))
    if hasattr(logging, methodName):
       raise AttributeError('{} already defined in logging module'.format(methodName))
    if hasattr(logging.getLoggerClass(), methodName):
       raise AttributeError('{} already defined in logger class'.format(methodName))

    # This method was inspired by the answers to Stack Overflow post
    # http://stackoverflow.com/q/2183233/2988730, especially
    # http://stackoverflow.com/a/13638084/2988730
    def logForLevel(self, message, *args, **kwargs):
        if self.isEnabledFor(levelNum):
            self._log(levelNum, message, args, **kwargs)
    def logToRoot(message, *args, **kwargs):
        logging.log(levelNum, message, *args, **kwargs)

    logging.addLevelName(levelNum, levelName)
    setattr(logging, levelName, levelNum)
    setattr(logging.getLoggerClass(), methodName, logForLevel)
    setattr(logging, methodName, logToRoot)


def parse_courses(course_strings, courses_taken, courses_in_progress, 
                  subject='PHY', 
                  valid_grades = ['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'NR']):
    
    skip_grades = ['F', 'NA', 'AU', 'WD']

    six_ninety_done = 0
    six_ninety_in_progress = 0
    
    for s in course_strings:
        line = s.split('(' + subject)[1:]
        for l in line:
            line_data = l.split(')')
            course_number = line_data[0]
            credits = int(float(line_data[3].split('(',1)[1]))
            grade = line_data[4].split('(',1)[1].strip()
            if grade in skip_grades:
                continue
            elif grade in valid_grades:
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


def parse_student(markdown, current_semester, suids):

    if len(re.findall('Undergrad', markdown)) > 0:
        return None

    result = {'Registration' : 'OK',
    'Program Status' : 'Active',
    'Comments' : '' }

    student_string = markdown.split('(Graduate Record)')[0]
    suid = int(re.findall(r'\([0-9]{5}-[0-9]{4}\)', markdown)[0][1:-1].replace('-',''))
    logging.student('\n======== {} ({}) '.format(suids[suid], suid))
    result['Name'] = suids[suid]
    result['SUID'] = suid

    if len(re.findall('\(All But Dissertation\)', markdown)) > 0:
        logging.debug('ABD Status')
        abd = True
        result['ABD'] = 'Yes'
    else:
        logging.debug('Not ABD Status')
        abd = False
        result['ABD'] = 'No'

    if len(re.findall('\(Qualifying Exam 1\)', markdown)) > 0:
        logging.debug('Passed written qualifying exam')
        pass_wqe = True
        result['Qualifier'] = 'Yes'
    else:
        logging.debug('Needs to take written qualifying exam')
        pass_wqe = False
        result['Qualifier'] = 'No'

    if len(re.findall('\(Qualifying Exam 2\)', markdown)) > 0:
        logging.debug('Passed research oral exam')
        pass_research_oral = True
        result['Research Oral'] = 'Yes'
    else:
        logging.debug('Needs to take research oral exam')
        pass_research_oral = False
        result['Research Oral'] = 'No'

    gpa_strings = re.findall(r'\(.*?\)',markdown.split(
        '(** Graduate Record Credit Summary **)', 1)[1].split(
        '(End of Graduate Record)')[0])

    for s in gpa_strings:
        desc, data = s.split(':')
        desc = desc[1:].strip()
        data = data[:-1].strip()
        if desc == 'Total Units Earned':
            credits_earned = int(float(data))
            logging.debug('Earned {} credits'.format(credits_earned))
        if desc == 'Transfer Credit':
            credits_transfered = int(float(data))
            logging.debug('Transferred {} credits'.format(credits_transfered))

    courses_taken = set()
    courses_in_progress = set()

    course_strings = markdown.split('-Physics)')
    courses_taken, courses_in_progress = parse_courses(course_strings, courses_taken, courses_in_progress)
    courses_taken, courses_in_progress = parse_courses(course_strings, courses_taken, courses_in_progress, 'MAT')
    courses_taken, courses_in_progress = parse_courses(course_strings, courses_taken, courses_in_progress, 'ECS')
    logging.debug('Courses taken: {}'.format(courses_taken))
    logging.debug('Courses in progress: {}'.format(courses_in_progress))

    current_semester_string = markdown.split(current_semester + '-Physics)')[-1:]
    c = set()
    t = set()
    c, t = parse_courses(current_semester_string, c, t, 'PHY', 'NR')
    c, t = parse_courses(current_semester_string, c, t, 'GRD', 'NR')
    c, t = parse_courses(current_semester_string, c, t, 'MAT', 'AU')
    c, t = parse_courses(current_semester_string, c, t, 'ECS', 'AU')
    c, t = parse_courses(current_semester_string, c, t, 'BEN', 'AU')
    current_courses = c.union(t)
    logging.debug('Current {} semester courses {}'.format(current_semester,courses_taken))

    required_core = {('PHY621',3), ('PHY641',3), ('PHY661',3), ('PHY662',3), ('PHY731',3)}
    if courses_taken.intersection(required_core) == required_core:
        logging.info('Completed required core class requirements')
        completed_core = True
        result['Core'] = 'Yes'
    else:
        logging.debug('Not yet completed required core class requirements')
        completed_core = False
        result['Core'] = 'No'

    required_skills_courses = {('PHY514',3), ('PHY614',3), ('PHY651',3)}
    if len(courses_taken.intersection(required_skills_courses)) > 0:
        logging.info('Completed required skills course requirements')
        completed_skills = True
        result['Skills'] = 'Yes'
    else:
        logging.debug('Not yet completed required skills course requirements')
        completed_skills = False
        result['Skills'] = 'No'

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
        logging.info('Completed required elective courses')
        has_electives = True
        result['Elective'] = 'Yes'
    else:
        has_electives = False
        result['Elective'] = 'No'
        logging.debug('Not yet completed required elective courses')

    missing_grades = courses_in_progress.difference(current_courses)
    if len(missing_grades):
        msg = 'Missing grades for {}. '.format(missing_grades)
        logging.critical(msg)
        result['Registration'] = 'Problem'
        result['Comments'] += msg

    if abd:
        logging.info("Has ABD status")
        grd_998 = {('GRD998',0)}
        if current_courses.intersection(grd_998) == grd_998:
            logging.info("Registered for GRD998")
        else:
            msg = 'ABD but registered for {}. '.format(current_courses)
            logging.critical(msg)
            result['Registration'] = 'Problem'
            result['Comments'] += msg

    if not abd and pass_wqe and pass_research_oral and completed_core and completed_skills:
        if credits_earned < 48:
            logging.info('Needs {} more credits for ABD status.'.format(48 - credits_earned))
        else:
            logging.critical('Needs to apply for ABD status.')
            result['ABD'] = 'Overdue'
        logging.info('Currently taking {}'.format(current_courses))

    if not abd and pass_wqe and pass_research_oral:
        if completed_core is False:
            logging.critical('Incomplete core class requirements')
        if completed_skills is False:
            logging.critical('Incomplete skills course requirements')

    reserch_oral_overdue = False
    if (pass_research_oral is False) and (credits_earned > 36):
        logging.critical('Overdue for research oral examination')
        reserch_oral_overdue = True
        result['Research Oral'] = 'Overdue'
    elif pass_wqe and pass_research_oral is False:
        logging.error('Needs to take research oral')

    credit_remaining = 48 - credits_earned
    pending_credit = 0
    pending_not_posted_credit = 0
    for c in current_courses:
        course, credit = c
        pending_not_posted_credit += credit
        if course != 'PHY999':
            pending_credit += credit

    if credit_remaining > -1 and (pending_credit > credit_remaining):
        msg = 'Over registered for classes: pending {}, remaining {}. '.format(pending_credit,credit_remaining)
        logging.critical(msg)
        result['Registration'] = 'Over'
        result['Comments'] += msg

    if pending_not_posted_credit < min(9, credit_remaining):
        msg = 'Insufficent registration for classes: pending {}, remaining {}. '.format(pending_not_posted_credit,credit_remaining)
        logging.critical(msg)
        result['Registration'] = 'Under'
        result['Comments'] += msg

    award = min(9, 48-(credits_earned+pending_credit))
    if award > 0:
        if reserch_oral_overdue is False and (pass_wqe is False or pass_research_oral is False) and award < 9:
            logging.critical('Check for registration error')
            result['Registration'] = 'Problem'
            result['Comments'] += 'Unresolved registration error. '
        logging.warning('Needs {} credit award next semester'.format(award))
        result['cred_award'] = award
    else:
        result['cred_award'] = 0

    logging.info('Currently taking {}'.format(current_courses))
    cred_remaining = max(0,48 - (credits_earned+pending_credit))
    logging.info('Needs {} more credits for ABD status.'.format(cred_remaining))
    result['cred_remaining'] = cred_remaining

    return result

if __name__ == '__main__':
    addLoggingLevel('STUDENT', logging.CRITICAL + 1)

    parser = argparse.ArgumentParser()
    parser.add_argument('--current-semester', help='current semester in transcript')
    parser.add_argument('--log-level', help='logging level', default='error')
    parser.add_argument('--transcript-file', help='PDF file containing MySlice advising transcripts', default='Transcripts.PDF')
    parser.add_argument('--active-student-file', help='Excel file contaiing active student data from MySlice query', default='Active Student Data.xls')
    parser.add_argument('--output-file', help='Excel file contaiing report on students for upload to Teams', default='Graduate Student Report.xlsx')
    args = parser.parse_args()

    if args.current_semester is None:
        raise ValueError('--current-semester must be specified')
    semesters = ['Fall', 'Spring', 'Summer']
    s, y = args.current_semester.split(' ')
    if s not in semesters:
        raise ValueError('--current-semester must be one of {} followed by the year'.format(semesters))
    if not re.match(r'[0-9]{4}',y):
        raise ValueError('Invalid year for --current-semester')

    numeric_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % loglevel)
    
    logging.basicConfig(level=numeric_level,format='%(levelname)s%(message)s')
    logging.addLevelName(logging.STUDENT, "")
    logging.addLevelName(logging.CRITICAL, "CRITICAL ")
    logging.addLevelName(logging.ERROR, "ERROR    ")
    logging.addLevelName(logging.WARNING, "WARNING  ")
    logging.addLevelName(logging.INFO, "INFO     ")

    active_student_csv = args.active_student_file.split('.')[0] + '.csv'
    data_xls = pd.read_excel(args.active_student_file, 0, index_col=None)
    data_xls.to_csv(active_student_csv, encoding='ascii', index=False)
    
    reader = csv.DictReader(open(active_student_csv))
    suids = {}
    citizenship = {}

    for row in reader:
        key = int(row['Emplid'])
        suids[key] = row['Name Last First Mid']
        citizenship[key] = row['Citizenship Sh Desc']
    
    fd = open(args.transcript_file,'rb')
    viewer = SimplePDFViewer(fd)
    
    data = []


    all_pages = [p for p in viewer.doc.pages()]
    for p in range(len(all_pages)):
        viewer.navigate(p+1)
        viewer.render()
        r = parse_student(viewer.canvas.text_content, args.current_semester, suids)
        if r is None:
            continue
        data.append([ r['Name'], str(r['SUID']),
        r['Program Status'], r['Registration'],
        r['cred_remaining'], r['cred_award'],
        citizenship[r['SUID']],
        r['Core'], r['Qualifier'], r['Skills'], 
        r['Research Oral'], r['Elective'], r['ABD'],
        r['Comments']])

    workbook = xlsxwriter.Workbook(args.output_file)
    worksheet = workbook.add_worksheet()
    worksheet.add_table('A1:N{}'.format(len(data)), 
        {'data' : data,
         'columns' : [{'header' : 'Name'}, 
                      {'header' : 'SUID'},
                      {'header' : 'Program Status'},
                      {'header' : 'Registration'},
                      {'header' : 'Credits Remaining'},
                      {'header' : 'Next Credit Award'},
                      {'header' : 'Citizenship'},
                      {'header' : 'Core'},
                      {'header' : 'Qualifier'},
                      {'header' : 'Skills'}, 
                      {'header' : 'Research Oral'},
                      {'header' : 'Elective'},
                      {'header' : 'ABD'},
                      {'header' : 'Comments'}]})
    workbook.close()
    
    sys.exit(0)
