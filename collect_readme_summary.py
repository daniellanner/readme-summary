from typing import NamedTuple
import os
import re
import sys


class FileSummary(NamedTuple):
    topic_name: str
    file_path: str
    summary: str

    collection = []  # static


def read_file_summary(file_to_read):
    with open(file_to_read, 'r') as file:
        data = file.read()

        # get the first headline
        result = re.search('# (.*)\n', data)
        if result:
            topic_name = result.group(1)
        else:
            topic_name = os.path.basename(os.path.dirname(file_to_read))

        # split file into header2 sections
        # we use the Introduction section as the short summary in our table
        split = data.split('## ')
        for it in split:
            if it.startswith('Introduction'):
                file_path = file_to_read.replace('\\', '/')
                summary = it.replace('Introduction\n', '', 1)

                # cleanup any dangling whitespace or sub-header
                while summary.endswith('#') or summary.endswith(' ') or summary.endswith('\n'):
                    summary = summary[:-1]

                FileSummary.collection.append(FileSummary(topic_name, file_path, summary))
                break


def resolve_relative_links(root_file):
    root_dir = os.path.dirname(root_file)

    for i in range(len(FileSummary.collection)):
        it = FileSummary.collection[i]
        rel_path = os.path.relpath(os.path.dirname(it.file_path), root_dir).replace('\\', '/')

        start_idx = 0

        while start_idx > -1:
            start_idx = it.summary.find("](", start_idx)
            if start_idx < 0:
                continue

            start_idx += 2
            end_idx = it.summary.find(")", start_idx)
            if end_idx < 0:
                continue

            link_body = it.summary[start_idx:end_idx]

            if link_body.startswith("https://"):
                continue

            updated_link_body = rel_path + "/" + link_body
            updated_summary = it.summary[:start_idx] + updated_link_body + it.summary[end_idx:]
            FileSummary.collection[i] = FileSummary.collection[i]._replace(summary=updated_summary)


def main(root_file):
    # generate collection of all table entries based on README.md in subdirectories
    for root, _, files in os.walk(os.path.dirname(root_file)):
        for current_file in files:
            if os.path.basename(current_file) == 'README.md' and root != root_file:
                read_file_summary(os.path.join(root, current_file))

    # post processing
    resolve_relative_links(root_file)

    # write generated table into given README.md
    with open(root_file, 'r+') as file:
        root_file_content = file.read()

        START_TABLE = '<!-- start generated table -->\n'
        END_TABLE = '<!-- end generated table -->\n'

        table_split = root_file_content.split(START_TABLE)
        before_split = table_split[0]

        table_split = root_file_content.split(END_TABLE)
        after_split = ''
        if len(table_split) > 1:
            after_split = table_split[1]

        file.seek(0)
        file.truncate()

        new_file_content = before_split
        new_file_content += START_TABLE

        if len(commit_hash) > 0:
            new_file_content += f'generated from commit {commit_hash}  \non {commit_date} at {commit_time}\n'
        new_file_content += '\n'

        for it in FileSummary.collection:
            rel_path = os.path.relpath(it.file_path, os.path.dirname(root_file)).replace('\\', '/')
            new_file_content += f"[{it.topic_name}]({rel_path})  \n{it.summary}  \n\n"

        new_file_content += END_TABLE
        new_file_content += after_split

        file.write(new_file_content)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("No README.md was passed as argument.")
        sys.exit()

    root_file = sys.argv[1]

    if not root_file.endswith('README.md'):
        print("Passed argument is not 'README.md'.")
        sys.exit()

    commit_hash = ''
    commit_date = ''
    commit_time = ''

    if len(sys.argv) > 4:
        commit_hash = sys.argv[2]
        commit_date = sys.argv[3]
        commit_time = sys.argv[4]

    main(root_file)
