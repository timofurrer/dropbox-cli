all: install

install:
	python setup.py install
readme:
	pandoc README.md --from markdown --to rst -o README.rst
sdist: readme
	python setup.py sdist
publish: readme
	python setup.py sdist register upload
