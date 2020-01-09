# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Utilitys for OSS-Fuzz infrastrcture."""
import os
import re
import subprocess

import helper
import repo_manager

# Refrence to OSS-Fuzz home repo
OSS_FUZZ_HOME = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def build_fuzzers_from_commit(project_name,
                              commit,
                              build_repo_manager,
                              engine='libfuzzer',
                              sanitizer='address',
                              architecture='x86_64'):
  """Builds a OSS-Fuzz fuzzer at a  specific commit SHA.
  Args:
    project_name: The OSS-Fuzz project name
    commit: The commit SHA to build the fuzzers at
    build_repo_manager: The OSS-Fuzz project's repo manager to be built at
    engine: The fuzzing engine to be used
    sanitizer: The fuzzing sanitizer to be used
    architecture: The system architiecture to be used for fuzzing
  Returns:
    True on successful build False on failure
  """
  try:
    build_repo_manager.checkout_commit(commit)
  except repo_manager.RepoManagerError as err:
    print('Exception while checking out commit %s: %s' % (commit, err))
    return False
  if helper.build_fuzzers_impl(
      project_name=project_name,
      clean=True,
      engine=engine,
      sanitizer=sanitizer,
      architecture=architecture,
      env_to_add=None,
      source_path=build_repo_manager.repo_dir,
      mount_location=os.path.join('/src', build_repo_manager.repo_name)):
    return False
  return True


def detect_main_repo(project_name, repo_name=None, commit=None, src_dir='/src'):
  """Checks a docker image for the main repo of an OSS-Fuzz project.

  Note: The default is repo name to detect the main repo if both commit and repo_name are present

  Args:
    project_name: The name of the oss-fuzz project
    repo_name: The name of the main repo in an OSS-Fuzz project
    commit: A commit SHA that is associated with the main repo
    src_dir: The location of the projects source on the docker image
  Returns:
    If found: The repo's origin, the repo's name
    If not found: None, None
  """
  if not repo_name and not commit:
    print('Error can not detect main repo without a repo_name or a commit.')
    return None, None

  if repo_name:
    helper.build_image_impl('base-builder')
  helper.build_image_impl(project_name)

  docker_image_name = 'gcr.io/oss-fuzz/' + project_name
  command_to_run = [
      'docker', 'run', '--rm', '-t', docker_image_name, 'python3',
      os.path.join(src_dir, 'detect_repo.py'), '--src_dir', src_dir
  ]
  if repo_name:
    command_to_run.extend(['--repo_name', repo_name])
  else:
    command_to_run.extend(['--example_commit', commit])
  out, return_code = execute(command_to_run)
  if return_code:
    print('Command %s failed.' % command_to_run)
    return None, None
  match = re.search(r'\bDetected repo: ([^ ]+) ([^ ]+)', out.rstrip())
  if match and match.group(1) and match.group(2):
    return match.group(1), match.group(2)
  print("No main repo found.")
  return None, None


def execute(command, location=None, check_result=False):
  """ Runs a shell command in the specified directory location.
  Args:
    command: The command as a list to be run
    location: The directory the command is run in
    check_result: Should an exception be thrown on failed command
  Returns:
    The stdout of the command, the error code
  Raises:
    RuntimeError: running a command resulted in an error
  """

  if not location:
    location = os.getcwd()
  process = subprocess.Popen(command, stdout=subprocess.PIPE, cwd=location)
  out, err = process.communicate()
  if check_result and (process.returncode or err):
    raise RuntimeError('Error: %s\n Command: %s\n Return code: %s\n Out: %s' %
                       (err, command, process.returncode, out))
  if out is not None:
    out = out.decode('ascii')
  return out, process.returncode
