// -*- mode:C++; tab-width:8; c-basic-offset:2; indent-tabs-mode:t -*-
// vim: ts=8 sw=2 smarttab
/*
 * Ceph - scalable distributed file system
 *
 * Copyright (C) 2017 Red Hat, Inc
 *
 * This is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License version 2.1, as published by the Free Software
 * Foundation.  See file COPYING.
 *
 */

#pragma once

#include <core/future.hh>

#include "Fwd.h"

class AuthAuthorizer;

namespace ceph::net {

class Dispatcher {
 public:
  virtual ~Dispatcher() {}

  virtual seastar::future<> ms_dispatch(ConnectionRef conn, MessageRef m) {
    return seastar::make_ready_future<>();
  }

  virtual seastar::future<> ms_handle_accept(ConnectionRef conn) {
    return seastar::make_ready_future<>();
  }

  virtual seastar::future<> ms_handle_connect(ConnectionRef conn) {
    return seastar::make_ready_future<>();
  }

  virtual seastar::future<> ms_handle_reset(ConnectionRef conn) {
    return seastar::make_ready_future<>();
  }

  virtual seastar::future<> ms_handle_remote_reset(ConnectionRef conn) {
    return seastar::make_ready_future<>();
  }

  virtual seastar::future<msgr_tag_t, bufferlist>
  ms_verify_authorizer(peer_type_t,
		       auth_proto_t,
		       bufferlist&) {
    return seastar::make_ready_future<msgr_tag_t, bufferlist>(0, bufferlist{});
  }
  virtual seastar::future<std::unique_ptr<AuthAuthorizer>>
  ms_get_authorizer(peer_type_t, bool force_new);
};

} // namespace ceph::net
