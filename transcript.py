#!/usr/local/bin/python

import sys
import re
import csv
from pdfreader import SimplePDFViewer
import logging


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
        return

    student_string = markdown.split('(Graduate Record)')[0]
    suid = int(re.findall(r'\([0-9]{5}-[0-9]{4}\)', markdown)[0][1:-1].replace('-',''))
    logging.student('====== ({}) {:<35} ======================'.format(suid, suids[suid]))

    if len(re.findall('\(All But Dissertation\)', markdown)) > 0:
        logging.debug('ABD Status')
        abd = True
    else:
        logging.debug('Not ABD Status')
        abd = False

    if len(re.findall('\(Qualifying Exam 1\)', markdown)) > 0:
        logging.debug('Passed written qualifying exam')
        pass_wqe = True
    else:
        logging.debug('Needs to take written qualifying exam')
        pass_wqe = False

    if len(re.findall('\(Qualifying Exam 2\)', markdown)) > 0:
        logging.debug('Passed research oral exam')
        pass_research_oral = True
    else:
        logging.debug('Needs to take research oral exam')
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
    current_courses = c.union(t)
    logging.debug('Current {} semester courses {}'.format(current_semester,courses_taken))

    required_core = {('PHY621',3), ('PHY641',3), ('PHY661',3), ('PHY662',3), ('PHY731',3)}
    if courses_taken.intersection(required_core) == required_core:
        logging.info('Completed required core class requirements')
        completed_core = True
    else:
        logging.debug('Not yet completed required core class requirements')
        completed_core = False

    required_lab = {('PHY514',3), ('PHY614',3), ('PHY651',3)}
    if len(courses_taken.intersection(required_lab)) > 0:
        logging.info('Completed required skills course requirements')
        completed_lab = True
    else:
        logging.debug('Not yet completed required skills course requirements')
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
        logging.info('Completed required elective courses')
        has_electives = True
    else:
        has_electives = False
        logging.debug('Not yet completed required elective courses')

    missing_grades = courses_in_progress.difference(current_courses)
    if len(missing_grades):
        logging.critical('Missing grades for {}'.format(missing_grades))

    if abd:
        logging.info("Has ABD status")
        grd_998 = {('GRD998',0)}
        if current_courses.intersection(grd_998) == grd_998:
            logging.info("Registered for GRD998")
        else:
            logging.error('ABD but registered for {}'.format(current_courses))
        return

    if pass_wqe and pass_research_oral and completed_core and completed_lab:
        if credits_earned < 48:
            logging.info('Needs {} more credits for ABD status.'.format(48 - credits_earned))
        else:
            logging.critical('Needs to apply for ABD status.')
        logging.info('Currently taking {}'.format(current_courses))
        return

    if pass_wqe and pass_research_oral:
        if completed_core is False:
            logging.critical('Incomplete core class requirements')
        if completed_lab is False:
            logging.critical('Incomplete skills course requirements')

    if (pass_research_oral is False) and (credits_earned > 36):
        logging.critical('Overdue for research oral examination')

    if pass_wqe and completed_core and completed_lab:
        logging.error('Needs to take research oral')

    credit_remaining = 48 - credits_earned
    pending_credit = 0
    pending_not_posted_credit = 0
    for c in current_courses:
        course, credit = c
        pending_not_posted_credit += credit
        if course != 'PHY999':
            pending_credit += credit

    if pending_credit > credit_remaining:
        logging.critical('Over registered for classes: pending {}, remaining {}'.format(pending_credit,credit_remaining))

    if pending_not_posted_credit < min(9, credit_remaining):
        logging.critical('Insufficent registration for classes: pending {}, remaining {}'.format(pending_not_posted_credit,credit_remaining))

    award = min(9, 48-(credits_earned+pending_credit))
    if award > 0:
        if (pass_wqe is False or pass_research_oral is False) and award < 9:
            logging.critical('Check for registration error')
        logging.warning('Needs {} credit award next semester'.format(award))

    logging.info('Currently taking {}'.format(current_courses))
    logging.info('Needs {} more credits for ABD status.'.format(48 - (credits_earned+pending_credit)))
    return

if __name__ == "__main__":
    addLoggingLevel('STUDENT', 100)
    
    current_semester = 'Fall 2020'
    logging.basicConfig(level=logging.WARNING,format='%(message)s')
    
    reader = csv.DictReader(open('Active Student Data.csv'))
    suids = {}
    for row in reader:
        key = int(row['Emplid'])
        suids[key] = row['Name Last First Mid']
    
    fd = open('Transcripts.PDF','rb')
    viewer = SimplePDFViewer(fd)
    
    all_pages = [p for p in viewer.doc.pages()]
    
    for p in range(len(all_pages)):
        viewer.navigate(p+1)
        viewer.render()
        parse_student(viewer.canvas.text_content, current_semester, suids)
    
    sys.exit(0)
