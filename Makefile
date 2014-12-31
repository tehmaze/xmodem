tests:
	tox

upload:
	python setup.py sdist upload
	python setup.py bdist_egg upload
	python setup.py build_sphinx upload_sphinx

