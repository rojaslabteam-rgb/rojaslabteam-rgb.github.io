---
layout: single
permalink: /guide/
title: "Guide"
author_profile: true
---

{% include base_path %}

This guide covers how to use and customize the lab website. Each topic below links to a full page with detailed instructions.

## Table of Contents

| Topic | Description |
| ----- | ----------- |
{% for item in site.data.guide_toc.items %}| [{{ item.title }}]({{ item.url }}) | {{ item.description }} |
{% endfor %}
