import csv
import os
import argparse
from glob import glob

exts = ['pdf', 'jpg', 'png', 'doc', 'docx']
titles = {'student_id': '学号', 'student_name': '姓名', 'attachment': '作业'}


def get_filename_mapping(received):
    """
    获取新旧文件名的映射关系
    ====================

    因为腾讯问卷收集的附件会被后台重新命名，这个函数可以通过对导出的附件进行重命名

    注意：按照腾讯问卷当前版本（截止自2021年3月22日）的特性，
         所有重复提交（包括提交后修改）的附件，只会保留最新提交的信息，所以旧提交的附件不会被更改名字

    :param received: 后台导出的csv文件，问卷统计信息
    :return: _name_map: 重命名规则
    """
    _name_map = dict()  # format: {old: new}

    with open(received, 'r') as f:
        rows = csv.reader(f)
        header = next(rows)

        # 获取含有关键词的列的id
        sid_x = header.index([y for y in filter(lambda x: titles['student_id'] in x, header)][0])
        name_x = header.index([y for y in filter(lambda x: titles['student_name'] in x, header)][0])
        link_x = header.index([y for y in filter(lambda x: titles['attachment'] in x, header)][0])

        for row in rows:
            # 避免同学输错前5位学号
            sid = '20216' + row[sid_x].strip()[-3:]
            name = row[name_x].strip()
            link = row[link_x].split('"')[1].strip()
            typename = row[link_x].split('"')[-2].split('.')[-1].strip()

            if args.directly:
                # 直接问卷附件下载版本
                old_name = row[link_x].split('"')[-2].strip()
            else:
                # 微云版本
                survey_id = link.split('=')[1].split('&')[0]
                question_id = link.split('=')[2].split('&')[0]
                filename = link.split('=')[3].split('&')[0]
                old_name = survey_id + '_' + question_id + '_' + filename

            new_name = sid + '_' + name + '.' + typename

            _name_map[old_name] = new_name

    return _name_map


def rename_record_homeworks(folder, filename_mapping):
    """
    重命名附件
    =========

    根据 get_filename_mapping 得到的文件名映射情况对附件进行重命名

    只重命名最新提交，剩下未重命名的附件为较旧的提交
    
    :param folder: 要处理的文件夹
    :param filename_mapping: 文件名映射关系
    :return: None
    """
    candidates = []
    for ext in exts:
        candidates.extend(glob(os.path.join(folder, '20216*.') + ext))
    for f in sorted(candidates):
        # 重命名
        old_name = f.split(os.sep)[-1]
        if old_name in filename_mapping.keys():
            os.rename(os.path.join(folder, old_name), os.path.join(folder, filename_mapping[old_name]))


def get_classmates_dict(classmates_csv):
    """
    获取所有同学的信息
    ===============

    根据全班同学名单获取学号和姓名信息，同时构造提交情况登记表(dict)

    :param classmates_csv: 全班同学名单，至少包含"学号"和"姓名"两项
    :return: classmates: 提交情况登记表，格式: { student_id : [False, name] }
    """
    if not os.path.exists(classmates_csv):
        print("仍未指定全班同学名单，请将全班同学名单的.csv文件放入同级文件夹以统计提交情况")
        return

    # 加载全班同学列表
    with open(classmates_csv, 'r') as f:
        rows = csv.reader(f)
        header = next(rows)

        # 获取[学号]对应的列id
        sid_idx = header.index([y for y in filter(lambda x: titles['student_id'] in x, header)][0])
        name_idx = header.index([y for y in filter(lambda x: titles['student_name'] in x, header)][0])

        # 默认所有人都没提交
        # 格式: { student_id : [False, name] }
        classmates = {row[sid_idx]: [False, row[name_idx]] for row in rows}

    return classmates


def get_submit_info(folder, classmates):
    """
    统计提交情况
    ==========

    :param folder: 要处理的文件夹
    :param classmates: 提交情况登记表
    :return: None
    """

    # 完全限定命名格式
    candidates = []
    for ext in exts:
        candidates.extend(glob(os.path.join(folder, '20216*.') + ext))
    for f in sorted(candidates):
        sid = f.split(os.sep)[-1].split('_')[0]
        if sid in classmates.keys():
            classmates[sid][0] = True

    s1 = [(k, v[1]) for k, v in classmates.items() if v[0] is True]
    s2 = [(k, v[1]) for k, v in classmates.items() if v[0] is False]

    print('{} - 目前已接收{}份作业'.format(args.folder.split(os.sep)[-1], len(s1)))

    # 缺交情况
    if len(s2) > 0:
        print('')
        print('未收到学号')
        print('=' * 8)
        if args.verbose:
            [print(sid, name) for (sid, name) in s2]
        else:
            [print(sid) for (sid, _) in s2]
    else:
        print('')
        print('本周已收齐')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--folder', default=os.getcwd(),
                        help='Name of folder which containing homeworks, default = os.getcwd() (the working path)')
    #                         存放本次作业的文件夹，                         默认值：运行本脚本时所处的目录
    parser.add_argument('-c', '--classmates', default=os.path.join(os.getcwd(), 'classmates.csv'),
                        help='Filename of which containing all classmates\' information, default = os.getcwd() (the working path)')
    #                         存放所有同学名单的.csv文件，                   默认值：运行本脚本时所处目录下的classmates.csv
    parser.add_argument('-d', '--directly', action='store_true',
                        help='File IS downloaded directly from Tencent WenJuan or NOT (from Tencent WeiYun), default: Not (from WeiYun)')
    #                         主要用来区分作业是从微云下载或直接从腾讯问卷后台下载，给定默认从微云下载，给定-d认为从后台下载
    #                         两种下载渠道的文件命名有所不同
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Print student name or NOT, default: Not')
    #                         设定是否要展示未交同学的姓名

    parser.set_defaults(directly=False, verbose=False)
    args = parser.parse_args()

    if not os.path.isabs(args.folder):
        args.folder = os.path.join(os.getcwd(), args.folder)

    if not os.path.isabs(args.classmates):
        args.folder = os.path.join(os.getcwd(), args.classmates)

    # 选取工作目录中名称按字典序排名的最后一个.csv文件
    # 如果工作目录中的.csv全都是下载下来的提交情况，这将选择最新的一份文件
    received_csv = sorted(glob(os.path.join(args.folder, '*.csv')))[-1]

    rename_record_homeworks(args.folder, get_filename_mapping(received_csv))

    get_submit_info(args.folder, get_classmates_dict(args.classmates))
